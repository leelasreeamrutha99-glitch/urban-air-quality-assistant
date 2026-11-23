# 🌿 Urban Air Quality Assistant

A Streamlit web app that helps people explore air quality in a city, view a 48-hour pollutant forecast, and understand readings in plain language.

## Features

- Search for a city or town.
- Display current European AQI, PM2.5, PM10, and other pollutant readings when available.
- Explore an hourly 48-hour outlook.
- Show simple, general activity guidance based on the reported European AQI.
- Optional Gemini-powered explainer for questions about the readings.

## Platform and technology

- **Platform:** Streamlit
- **Language:** Python
- **Data:** Open-Meteo Geocoding API and Air Quality API
- **Optional AI assistant:** Google Gemini through the Google Gen AI SDK

The basic air-quality dashboard does not require an API key.

## Run locally

1. Install Python 3.10 or newer.
2. Clone this repository:

   `git clone https://github.com/leelasreeamrutha99-glitch/urban-air-quality-assistant.git`

3. Open the project folder:

   `cd urban-air-quality-assistant`

4. Install dependencies:

   `pip install -r requirements.txt`

5. Start the app:

   `streamlit run app.py`

6. Open the local URL shown in the terminal (usually http://localhost:8501).

## Enable the optional Gemini assistant

1. Create an API key in [Google AI Studio](https://aistudio.google.com/).
2. Set it as an environment variable named `GOOGLE_API_KEY`.

   **Windows PowerShell**
   ```powershell
   $env:GOOGLE_API_KEY="your_api_key_here"
   streamlit run app.py
   ```

   **macOS / Linux**
   ```bash
   export GOOGLE_API_KEY="your_api_key_here"
   streamlit run app.py
   ```

   Never commit API keys or paste them into source code.

## Deploy on Streamlit Community Cloud

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
2. Choose **New app** and connect this GitHub repository.
3. Select the `main` branch and `app.py` as the entry point.
4. Deploy. If using Gemini, add `GOOGLE_API_KEY` under the app's Secrets settings.

## Data and limitations

- Air-quality data is supplied by Open-Meteo and depends on upstream model availability.
- Forecast values are estimates and may differ from local monitoring stations.
- AQI interpretation varies by country and index. This starter app uses the European AQI scale for its general guidance.
- This project is for awareness and education only, not medical diagnosis or emergency advice.

## Possible Prompt Wars enhancements

- Add a map with multiple city comparisons.
- Add a cleanest-time-to-go-out recommendation.
- Add user-selected sensitivity profiles and accessible explanations.
- Add charts comparing locations and downloadable reports.
