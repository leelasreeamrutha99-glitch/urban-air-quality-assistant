# 🌿 Urban Air Quality Assistant

A Streamlit application that helps people explore city air quality, understand pollutant readings, and identify a lower-AQI time window in the next 48 hours.

## Features

- City search with input validation and clear no-result handling.
- Current European AQI, PM2.5, PM10, and other pollutant readings where supplied by the data source.
- Interactive 48-hour forecast chart and data table.
- General health-awareness guidance based on European AQI.
- Three-hour lower-AQI outdoor window recommendation when forecast AQI values are available.
- Optional Gemini-powered plain-language explainer.
- Cached API responses to reduce repeated requests.
- Automated unit tests and GitHub Actions quality checks.

## Technology

- Python and Streamlit
- Open-Meteo Geocoding API and Air Quality API
- Pandas and Requests
- Google Gemini via Google Gen AI SDK (optional)

The dashboard does not require a Gemini API key. The optional AI explainer requires a secret named `GOOGLE_API_KEY`.

## Run locally

Requires Python 3.10 or newer.

```bash
git clone https://github.com/leelasreeamrutha99-glitch/urban-air-quality-assistant.git
cd urban-air-quality-assistant
python -m venv .venv
```

Activate the virtual environment, then run:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Run tests

```bash
pytest -q
python -m compileall -q app.py air_quality.py tests
```

Tests cover input validation, API response handling, AQI guidance, forecast parsing, and lower-AQI window calculation. GitHub Actions runs tests and syntax checks on pushes and pull requests to `main`.

## Configure Gemini (optional)

1. Create an API key in [Google AI Studio](https://aistudio.google.com/).
2. In Streamlit Community Cloud, open the app's **Settings → Secrets** and add:

```toml
GOOGLE_API_KEY = "your_api_key_here"
```

For local development, set the `GOOGLE_API_KEY` environment variable. Never commit API keys or paste them into source code.

## Deploy

1. Open [Streamlit Community Cloud](https://share.streamlit.io/).
2. Select this repository, branch `main`, and entry point `app.py`.
3. Deploy the app.
4. Add `GOOGLE_API_KEY` in the app's Secrets only if you want Gemini enabled.

## Data quality, safety, and limitations

- Air-quality values and forecasts come from Open-Meteo and depend on upstream model availability.
- Forecasts are estimates and can differ from local ground-monitoring stations.
- The lower-AQI window compares values within the returned forecast; it does not guarantee safe air or provide medical advice.
- AQI scales differ by country. This project labels and interprets the European AQI field.
- The app is for education and general awareness, not diagnosis, treatment, or emergency advice. Follow official local alerts.

## Accessibility and security practices

- Form controls have explicit labels and helper text.
- Key information is available as text and a data table, not only through a chart or colour.
- Input length and coordinate ranges are validated.
- API calls use timeouts; unexpected upstream failures are logged server-side and shown as safe, generic messages.
- API credentials are read from environment variables or Streamlit secrets and are never displayed.
- API data is cached for bounded periods to reduce repeated requests.

## Further improvements

- Add a map and side-by-side city comparisons.
- Add localization and AQI scale selection for different countries.
- Add downloadable reports and test with screen readers and keyboard-only navigation.
