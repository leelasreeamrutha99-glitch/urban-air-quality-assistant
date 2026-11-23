import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Urban Air Quality Assistant", page_icon="🌿", layout="wide")

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

POLLUTANTS = {
    "pm2_5": ("PM2.5", "µg/m³"),
    "pm10": ("PM10", "µg/m³"),
    "nitrogen_dioxide": ("Nitrogen dioxide", "µg/m³"),
    "ozone": ("Ozone", "µg/m³"),
    "carbon_monoxide": ("Carbon monoxide", "µg/m³"),
    "sulphur_dioxide": ("Sulphur dioxide", "µg/m³"),
    "european_aqi": ("European AQI", ""),
}


def get_city(name: str) -> dict:
    response = requests.get(
        GEO_URL,
        params={"name": name, "count": 1, "language": "en", "format": "json"},
        timeout=15,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise ValueError(f'No matching city found for "{name}". Try another spelling.')
    return results[0]


def get_air_quality(latitude: float, longitude: float, timezone: str) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(POLLUTANTS.keys()),
        "hourly": ",".join(POLLUTANTS.keys()),
        "forecast_days": 2,
        "timezone": timezone or "auto",
    }
    response = requests.get(AIR_URL, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def advice_for(aqi):
    if aqi is None or pd.isna(aqi):
        return "AQI data is unavailable. Check again later."
    aqi = float(aqi)
    if aqi <= 20:
        return "Air quality is good. Enjoy your usual outdoor activities."
    if aqi <= 40:
        return "Air quality is fair. Most people can continue normal outdoor activities."
    if aqi <= 60:
        return "Sensitive people should consider reducing prolonged, strenuous outdoor activity."
    if aqi <= 80:
        return "Consider limiting prolonged outdoor exertion, especially if you are sensitive to air pollution."
    if aqi <= 100:
        return "Reduce prolonged outdoor activity. Consider a well-fitting mask if you must be outside."
    return "Air quality may be poor. Avoid strenuous outdoor activity and follow local health advisories."


def build_forecast(data: dict) -> pd.DataFrame:
    hourly = data.get("hourly", {})
    if not hourly or "time" not in hourly:
        return pd.DataFrame()
    frame = pd.DataFrame({"time": pd.to_datetime(hourly["time"])})
    for key in ("pm2_5", "pm10", "european_aqi"):
        if key in hourly:
            frame[key] = hourly[key]
    return frame


st.title("🌿 Urban Air Quality Assistant")
st.caption("Check current air pollution, explore the next 48 hours, and plan outdoor activities more thoughtfully.")

with st.sidebar:
    st.header("Find a location")
    city_name = st.text_input("City or town", value="Kakinada")
    search = st.button("Check air quality", type="primary", use_container_width=True)
    st.divider()
    st.caption("Data source: Open-Meteo Air Quality API. Forecasts are estimates, not medical advice.")

if "city_name" not in st.session_state:
    st.session_state.city_name = "Kakinada"
if search:
    st.session_state.city_name = city_name.strip()

selected_city = st.session_state.city_name
if not selected_city:
    st.info("Enter a city in the sidebar to begin.")
    st.stop()

try:
    with st.spinner(f"Fetching air quality for {selected_city}..."):
        place = get_city(selected_city)
        air = get_air_quality(place["latitude"], place["longitude"], place.get("timezone", "auto"))
except (requests.RequestException, ValueError, KeyError) as error:
    st.error(f"Could not load air-quality data: {error}")
    st.stop()

st.subheader(f'{place["name"]}, {place.get("admin1", "")} {place.get("country", "")}')
st.caption(f'Coordinates: {place["latitude"]:.3f}, {place["longitude"]:.3f}')

current = air.get("current", {})
current_units = air.get("current_units", {})
aqi = current.get("european_aqi")

metric_keys = ["european_aqi", "pm2_5", "pm10", "nitrogen_dioxide"]
columns = st.columns(len(metric_keys))
for column, key in zip(columns, metric_keys):
    label, default_unit = POLLUTANTS[key]
    value = current.get(key)
    unit = current_units.get(key, default_unit)
    column.metric(label, "—" if value is None else f"{value:g} {unit}")

st.info(advice_for(aqi))

st.subheader("48-hour outlook")
forecast = build_forecast(air)
if forecast.empty:
    st.warning("Hourly forecast data is not available right now.")
else:
    selected_pollutant = st.selectbox(
        "Choose a measurement",
        options=["european_aqi", "pm2_5", "pm10"],
        format_func=lambda key: POLLUTANTS[key][0],
    )
    if selected_pollutant in forecast:
        chart_data = forecast.set_index("time")[[selected_pollutant]].rename(
            columns={selected_pollutant: POLLUTANTS[selected_pollutant][0]}
        )
        st.line_chart(chart_data)
    st.dataframe(forecast, use_container_width=True, hide_index=True)

st.subheader("AI air-quality explainer")
st.write("Ask for a plain-language explanation of the current readings. Add a Google AI Studio API key to enable the optional Gemini assistant.")
question = st.text_input("Your question", placeholder="What do these readings mean for a morning walk?")
if st.button("Ask assistant") and question.strip():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.warning("Gemini is not configured yet. Add GOOGLE_API_KEY to your environment or Streamlit secrets.")
    else:
        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            prompt = (
                "You are a cautious air-quality explainer. Explain the readings in simple language. "
                "Do not diagnose or make guarantees. Encourage users with health concerns to follow "
                "local public-health advice.\n"
                f"Location: {place['name']}, {place.get('country', '')}\n"
                f"Current readings: {current}\nQuestion: {question}"
            )
            with st.spinner("Generating an explanation..."):
                answer = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.write(answer.text or "No response was returned.")
        except Exception as error:
            st.error(f"Gemini request failed: {error}")

st.divider()
st.caption("This tool is for general awareness only. It is not a medical device and should not replace official local air-quality alerts.")
