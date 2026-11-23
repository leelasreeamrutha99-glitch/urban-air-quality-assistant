import pandas as pd
import pytest

from air_quality import (
    AIR_URL,
    GEO_URL,
    CityNotFoundError,
    advice_for,
    best_outdoor_window,
    build_forecast,
    get_air_quality,
    get_city,
    validate_city_name,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def test_city_name_is_trimmed():
    assert validate_city_name("  Kakinada  ") == "Kakinada"


@pytest.mark.parametrize("name", ["", " ", "a", "x" * 81, "bad\ncity"])
def test_invalid_city_name_is_rejected(name):
    with pytest.raises(ValueError):
        validate_city_name(name)


def test_get_city_returns_first_result_and_sets_timeout():
    session = FakeSession({"results": [{"name": "Kakinada", "latitude": 16.9, "longitude": 82.2}]})
    result = get_city("Kakinada", session=session)
    assert result["name"] == "Kakinada"
    assert session.calls[0][0] == GEO_URL
    assert session.calls[0][1]["timeout"] == (5, 20)


def test_get_city_raises_for_no_match():
    with pytest.raises(CityNotFoundError):
        get_city("NoSuchCity", session=FakeSession({"results": []}))


def test_get_air_quality_rejects_invalid_coordinates():
    with pytest.raises(ValueError):
        get_air_quality(120, 0)


def test_get_air_quality_requests_current_and_forecast():
    session = FakeSession({"current": {"european_aqi": 25}, "hourly": {}})
    payload = get_air_quality(16.9, 82.2, session=session)
    assert payload["current"]["european_aqi"] == 25
    assert session.calls[0][0] == AIR_URL
    assert session.calls[0][1]["params"]["forecast_days"] == 2


@pytest.mark.parametrize(
    ("aqi", "expected"),
    [
        (None, "unavailable"),
        (10, "good"),
        (30, "fair"),
        (50, "sensitive"),
        (70, "consider"),
        (90, "reduce"),
        (120, "poor"),
    ],
)
def test_aqi_guidance(aqi, expected):
    assert expected in advice_for(aqi).lower()


def test_build_forecast_converts_numeric_values_and_drops_bad_time():
    result = build_forecast(
        {
            "hourly": {
                "time": ["2026-01-01T00:00", "not-a-date"],
                "european_aqi": [10, 20],
                "pm2_5": ["1.2", "2.3"],
            }
        }
    )
    assert len(result) == 1
    assert result.loc[0, "european_aqi"] == 10
    assert result.loc[0, "pm2_5"] == pytest.approx(1.2)


def test_build_forecast_handles_missing_data():
    assert build_forecast({}).empty


def test_best_outdoor_window_returns_lowest_average():
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=5, freq="h"),
            "european_aqi": [70, 60, 10, 12, 14],
        }
    )
    assert best_outdoor_window(frame) == "Thu, 01 Jan 02:00–04:00"


def test_best_outdoor_window_handles_missing_values():
    frame = pd.DataFrame(
        {"time": pd.date_range("2026-01-01", periods=3, freq="h"), "european_aqi": [None, None, None]}
    )
    assert best_outdoor_window(frame) is None
