"""Validated API access and reusable logic for the air-quality application."""
from __future__ import annotations

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


def validate_city_name(name: str) -> str:
    city = name.strip()
    if not 2 <= len(city) <= 80:
        raise ValueError("Enter a city name between 2 and 80 characters.")
    if any(ord(char) < 32 for char in city):
        raise ValueError("The city name contains unsupported characters.")
    return city


def get_city(name: str, session: Any = requests) -> dict:
    city = validate_city_name(name)
    response = session.get(
        GEO_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        raise CityNotFoundError(f'No matching city found for "{city}". Try another spelling.')
    return results[0]


def get_air_quality(latitude: float, longitude: float, timezone: str = "auto", session: Any = requests) -> dict:
    if not (-90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180):
        raise ValueError("Invalid geographic coordinates.")
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(POLLUTANTS),
        "hourly": ",".join(POLLUTANTS),
        "forecast_days": 2,
        "timezone": timezone or "auto",
    }
    response = session.get(AIR_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("current"), dict):
        raise ValueError("The air-quality service returned an unexpected response.")
    return payload


def advice_for(aqi: float | int | None) -> str:
    if aqi is None or pd.isna(aqi):
        return "AQI data is unavailable. Check again later."
    value = float(aqi)
    if value < 0:
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
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return pd.DataFrame(columns=["time"])
    frame = pd.DataFrame({"time": pd.to_datetime(times, errors="coerce")})
    for key in ("european_aqi", "pm2_5", "pm10", "nitrogen_dioxide", "ozone"):
        values = hourly.get(key)
        if values is not None and len(values) == len(frame):
            frame[key] = pd.to_numeric(pd.Series(values), errors="coerce")
    return frame.dropna(subset=["time"]).reset_index(drop=True)


def best_outdoor_window(forecast: pd.DataFrame, hours: int = 3) -> str | None:
    """Find the lowest-average consecutive AQI window in the supplied forecast."""
    if hours < 1 or "european_aqi" not in forecast or "time" not in forecast or len(forecast) < hours:
        return None
    values = pd.to_numeric(forecast["european_aqi"], errors="coerce")
    rolling = values.rolling(window=hours, min_periods=hours).mean()
    if rolling.isna().all():
        return None
    end_index = int(rolling.idxmin())
    start_index = end_index - hours + 1
    start = pd.to_datetime(forecast.iloc[start_index]["time"])
    end = pd.to_datetime(forecast.iloc[end_index]["time"])
    return f"{start:%a, %d %b %H:%M}–{end:%H:%M}"
