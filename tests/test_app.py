"""Route tests for app.py using mock METAR readings.

The weather API is never called. ``requests.get`` is patched to return canned
JSON shaped like the real aviationweather.gov response, so each test checks
how a specific METAR reading comes out on the page.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from app import app


def make_record(**overrides):
    """Build a mock API record. Defaults describe a calm, clear day at KHIO."""
    record = {
        "icaoId": "KHIO",
        "reportTime": "2026-10-12T20:00:00.000Z",
        "temp": 15,
        "dewp": 5.6,
        "wdir": 0,
        "wspd": 0,
        "visib": "10+",
        "altim": 1017.7,
        "rawOb": "METAR KHIO 121953Z 00000KT 10SM CLR 15/06 A3005",
        "name": "Portland/Hillsboro Arpt, OR, US",
        "cover": "CLR",
        "clouds": [],
        "fltCat": "VFR",
    }
    record.update(overrides)
    return record


def mock_response(records=None, *, body=None, http_error=False):
    """Build a fake ``requests`` response.

    ``records`` is a list of API records. ``body`` overrides the raw bytes
    (use ``b""`` to mimic the API's empty reply for unknown stations).
    """
    response = MagicMock()
    response.content = body if body is not None else b"[...]"
    response.json.return_value = records if records is not None else []
    if http_error:
        response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    return response


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def lookup(client, code, response):
    """Post a code with ``requests.get`` patched. Returns (http_response, mock_get)."""
    with patch("app.requests.get", return_value=response) as mock_get:
        return client.post("/metar", data={"code": code}), mock_get


# --- METAR readings are interpreted correctly ------------------------------

# Each case: the API record fields to override, and text the page must show.
READINGS = {
    "clear_and_calm": (
        {},
        ["Clear skies, 59 degrees, calm, with little or no wind.", "59°F (15°C), mild", "30.05 inHg"],
    ),
    "windy_south_with_gusts": (
        {"wdir": 180, "wspd": 10, "wgst": 20},
        ["12 mph from the south, gusting to 23 mph"],
    ),
    "overcast_light_rain": (
        {"wxString": "-RA", "cover": "OVC", "clouds": [{"cover": "OVC", "base": 1500}]},
        ["Light rain", "Overcast at 1,500 ft"],
    ),
    "heavy_thunderstorm": (
        {"wxString": "+TSRA", "cover": "BKN", "clouds": [{"cover": "BKN", "base": 3000}]},
        ["Heavy thunderstorm with rain", "Mostly cloudy at 3,000 ft"],
    ),
    "freezing_fog_low_visibility": (
        {"temp": -4, "wxString": "FZFG", "visib": 0.25, "fltCat": "LIFR"},
        ["25°F (-4°C), cold", "Freezing fog", "0.25 miles, poor visibility", "Very poor visibility for flying"],
    ),
    "fractional_visibility_fog": (
        {"wxString": "FG", "visib": "1/4", "fltCat": "LIFR"},
        ["0.25 miles, poor visibility", "Fog"],
    ),
    "showers_nearby": (
        {"wxString": "VCSH"},
        ["Showers nearby"],
    ),
    "variable_wind": (
        {"wdir": "VRB", "wspd": 4},
        ["5 mph from a changing direction"],
    ),
    "hot_afternoon": (
        {"temp": 38, "dewp": 12, "wdir": 270, "wspd": 8},
        ["100°F (38°C), very hot", "9 mph from the west"],
    ),
}


@pytest.mark.parametrize("name", READINGS)
def test_reading_is_decoded(client, name):
    overrides, expected = READINGS[name]
    response, _ = lookup(client, "KHIO", mock_response([make_record(**overrides)]))

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    for text in expected:
        assert text in page


def test_page_shows_station_name_and_raw_metar(client):
    response, _ = lookup(client, "KHIO", mock_response([make_record()]))

    page = response.get_data(as_text=True)
    assert "Portland/Hillsboro Arpt, OR, US" in page
    assert "METAR KHIO 121953Z 00000KT 10SM CLR 15/06 A3005" in page
    assert "20:00 UTC on Oct 12, 2026" in page


# --- Input handling and API request ----------------------------------------

@pytest.mark.parametrize(
    "typed, expected_station",
    [("KHIO", "KHIO"), ("khio", "KHIO"), ("  hio  ", "KHIO"), ("HIO", "KHIO")],
)
def test_code_is_normalized_before_calling_api(client, typed, expected_station):
    _, mock_get = lookup(client, typed, mock_response([make_record()]))

    assert mock_get.call_args.kwargs["params"] == {"ids": expected_station, "format": "json"}


def test_get_query_string_also_works(client):
    with patch("app.requests.get", return_value=mock_response([make_record()])):
        response = client.get("/metar?code=KHIO")

    assert response.status_code == 200
    assert "Clear skies" in response.get_data(as_text=True)


@pytest.mark.parametrize("bad_code", ["", "!!", "AB", "KHIOX", "K H"])
def test_invalid_code_returns_400_without_calling_api(client, bad_code):
    response, mock_get = lookup(client, bad_code, mock_response())

    assert response.status_code == 400
    assert "3 or 4 letters" in response.get_data(as_text=True)
    mock_get.assert_not_called()


# --- Errors from the weather service ---------------------------------------

@pytest.mark.parametrize(
    "api_reply",
    [mock_response(body=b""), mock_response([])],
    ids=["empty_body", "empty_list"],
)
def test_unknown_station_returns_404(client, api_reply):
    response, _ = lookup(client, "ZZZZ", api_reply)

    assert response.status_code == 404
    assert "No weather report found for ZZZZ" in response.get_data(as_text=True)


@pytest.mark.parametrize(
    "failure",
    [
        {"side_effect": requests.Timeout()},
        {"side_effect": requests.ConnectionError()},
        {"return_value": mock_response(http_error=True)},
    ],
    ids=["timeout", "connection_error", "http_500"],
)
def test_api_failure_returns_502(client, failure):
    with patch("app.requests.get", **failure):
        response = client.post("/metar", data={"code": "KHIO"})

    assert response.status_code == 502
    assert "isn't responding" in response.get_data(as_text=True).replace("&#39;", "'")


def test_landing_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "METAR Weather Reader" in response.get_data(as_text=True)
