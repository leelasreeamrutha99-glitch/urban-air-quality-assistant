"""Validated API access and reusable logic for the air-quality application."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd
import requests

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
REQUEST_TIMEOUT = (5, 20)

POLLUTANTS = {
    "european_aqi": ("European AQI", ""),
    "pm2_5": ("PM2.5", "µg/m³"),
    "pm10": ("PM10", "µg/m³"),
    "nitrogen_dioxide": ("Nitrogen dioxide", "µg/m³"),
    "ozone": ("Ozone", "µg/m³"),
    "carbon_monoxide": ("Carbon monoxide", "µg/m³"),
    "sulphur_dioxide": ("Sulphur dioxide", "µg/m³"),
}


class CityNotFoundError(ValueError):
    """Raised when the geocoding service has no match for a city."""


class UpstreamResponseError(ValueError):
    """Raised when an external API returns an unusable response."""


def validate_city_name(name: str) -> str:
    """Normalize and validate a user-supplied city name."""
    if not isinstance(name, str):
        raise ValueError("Enter a valid city or town name.")
    city = name.strip()
    if not 2 <= len(city) <= 80:
        raise ValueError("Enter a city name between 2 and 80 characters.")
    if any(ord(char) < 32 for char in city):
        raise ValueError("The city name contains unsupported characters.")
    return city


def validate_coordinates(latitude: Any, longitude: Any) -> tuple[float, float]:
    """Return finite, in-range coordinates or raise a clear validation error."""
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Invalid geographic coordinates.") from error
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError("Invalid geographic coordinates.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Invalid geographic coordinates.")
    return lat, lon


def get_city(name: str, session: Any = requests) -> dict:
    """Look up a city using Open-Meteo geocoding."""
    city = validate_city_name(name)
    response = session.get(
        GEO_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise UpstreamResponseError("The location service returned an unexpected response.")
    results = payload.get("results")
    if results is None or results == []:
        raise CityNotFoundError(f'No matching city found for "{city}". Try another spelling.')
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise UpstreamResponseError("The location service returned an unexpected response.")
    place = results[0]
    validate_coordinates(place.get("latitude"), place.get("longitude"))
    return place


def get_air_quality(
    latitude: float,
    longitude: float,
    timezone: str = "auto",
    session: Any = requests,
) -> dict:
    """Fetch current and hourly air-quality data with bounded network timeouts."""
    lat, lon = validate_coordinates(latitude, longitude)
    safe_timezone = timezone or "auto"
    if (
        not isinstance(safe_timezone, str)
        or len(safe_timezone) > 64
        or any(ord(char) < 32 for char in safe_timezone)
    ):
        raise ValueError("Invalid timezone.")
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join(POLLUTANTS),
        "hourly": ",".join(POLLUTANTS),
        "forecast_days": 2,
        "timezone": safe_timezone,
    }
    response = session.get(AIR_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("current"), dict):
        raise UpstreamResponseError("The air-quality service returned an unexpected response.")
    hourly = payload.get("hourly")
    if hourly is not None and not isinstance(hourly, dict):
        raise UpstreamResponseError("The air-quality service returned an unexpected forecast.")
    return payload


def advice_for(aqi: float | int | None) -> str:
    """Provide cautious, general guidance for the European AQI value."""
    if aqi is None or pd.isna(aqi):
        return "AQI data is unavailable. Check again later."
    try:
        value = float(aqi)
    except (TypeError, ValueError, OverflowError):
        return "AQI data is unavailable. Check again later."
    if not math.isfinite(value) or value < 0:
        return "AQI data is invalid. Check again later."
    if value <= 20:
        return "Air quality is good. Enjoy your usual outdoor activities."
    if value <= 40:
        return "Air quality is fair. Most people can continue normal outdoor activities."
    if value <= 60:
        return "Sensitive people should consider reducing prolonged, strenuous outdoor activity."
    if value <= 80:
        return "Consider limiting prolonged outdoor exertion, especially if you are sensitive to air pollution."
    if value <= 100:
        return "Reduce prolonged outdoor activity. Follow local public-health advice if you are sensitive."
    return "Air quality may be poor. Avoid strenuous outdoor activity and follow local health advisories."


def build_forecast(data: dict) -> pd.DataFrame:
    """Convert the API's hourly arrays into a clean, consistently indexed table."""
    hourly = data.get("hourly") or {}
    if not isinstance(hourly, dict):
        return pd.DataFrame(columns=["time"])
    times = hourly.get("time") or []
    if not isinstance(times, list) or not times:
        return pd.DataFrame(columns=["time"])
    frame = pd.DataFrame({"time": pd.to_datetime(times, errors="coerce")})
    for key in ("european_aqi", "pm2_5", "pm10", "nitrogen_dioxide", "ozone"):
        values = hourly.get(key)
        if isinstance(values, list) and len(values) == len(frame):
            frame[key] = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy()
    return frame.dropna(subset=["time"]).reset_index(drop=True)


def best_outdoor_window(forecast: pd.DataFrame, hours: int = 3) -> str | None:
    """Find the lowest-average AQI window containing consecutive hourly records."""
    if (
        not isinstance(hours, int)
        or isinstance(hours, bool)
        or hours < 1
        or "european_aqi" not in forecast
        or "time" not in forecast
        or len(forecast) < hours
    ):
        return None

    values = pd.to_numeric(forecast["european_aqi"], errors="coerce").to_numpy()
    times = pd.to_datetime(forecast["time"], errors="coerce")
    best: tuple[float, int] | None = None

    for start in range(len(forecast) - hours + 1):
        end = start + hours
        window_values = values[start:end]
        window_times = times.iloc[start:end]
        if not all(math.isfinite(float(value)) for value in window_values):
            continue
        if window_times.isna().any():
            continue
        differences = window_times.diff().dropna()
        if not differences.eq(pd.Timedelta(hours=1)).all():
            continue
        average = float(sum(window_values) / hours)
        if best is None or average < best[0]:
            best = (average, start)

    if best is None:
        return None
    start_time = times.iloc[best[1]]
    end_time = times.iloc[best[1] + hours - 1]
    return f"{start_time:%a, %d %b %H:%M}–{end_time:%H:%M}"
