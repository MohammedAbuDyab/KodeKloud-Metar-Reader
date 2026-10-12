# METAR Reader

A small Flask web app that turns airport weather reports into plain English.

METAR is the standard weather report format used in aviation. It's compact and cryptic:

```
METAR KHIO 121953Z 00000KT 10SM CLR 15/06 A3005 RMK AO2 SLP175 T01500056
```

Type an airport code and METAR Reader shows you this instead:

> Clear skies, 59 degrees, calm, with little or no wind.

The page also lists temperature (°F and °C), wind in mph, visibility, sky layers, current conditions like rain or fog, dew point, pressure, and flight category. The original METAR is shown at the bottom.

## Requirements

- Python 3.10 or newer
- Internet access (the app calls a public weather API)

## Run it locally

```bash
git clone https://github.com/MohammedAbuDyab/KodeKloud-Metar-Reader.git
cd KodeKloud-Metar-Reader

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python app.py
```

Open http://127.0.0.1:5000 and enter a code such as `KHIO`, `KLAX`, or `KJFK`.

For development, set `FLASK_DEBUG=1` to get auto-reload and error pages. Don't enable debug mode on a public server.

## Run the tests

```bash
pytest
```

The tests cover the decoder: clear and calm conditions, wind direction and gusts, rain, variable wind, and thunderstorms. They don't call the network.

## How it works

1. **Input.** You enter a 3 or 4 character airport code. US airports work without the leading `K`, so `HIO` and `KHIO` are the same.
2. **Fetch.** `app.py` requests the latest report from the [Aviation Weather Center API](https://aviationweather.gov/data/api/) at `https://aviationweather.gov/api/data/metar?ids=KHIO&format=json`. The JSON format returns the report already split into fields (temperature, wind, clouds), which is more reliable than parsing the raw text.
3. **Decode.** `decoder.py` converts those fields into readable text: Celsius to Fahrenheit, knots to mph, wind degrees to a compass direction, and cloud and weather codes to words.
4. **Display.** Flask renders the result with Jinja templates.

### Project layout

| Path | Purpose |
| --- | --- |
| `app.py` | Flask routes, input validation, and the API call |
| `decoder.py` | Turns an API record into plain-English strings |
| `templates/base.html` | Shared page layout and styles |
| `templates/index.html` | Landing page with the airport code form |
| `templates/result.html` | Decoded weather report page |
| `tests/test_decoder.py` | Unit tests for the decoder |

### Routes

| Route | Method | Description |
| --- | --- | --- |
| `/` | GET | Landing page |
| `/metar` | GET, POST | Look up a code (`?code=KHIO` or a form post) |

`/metar` returns `400` for a malformed code, `404` when the station has no report, and `502` when the weather API is unreachable.

## Notes and limits

- **Wind direction is where the wind comes from.** "From the south" means a south wind blowing north. This is the standard meteorological convention.
- **Not for flight planning.** This app is a friendly summary. Pilots must use official sources for flight decisions.
- **Data freshness.** Most airports update about once an hour. The app shows the newest report the API has, and it can be older at small or remote airports.
- **Rate limits.** The app makes one API request per lookup and doesn't cache. If you expect heavy traffic, add caching and review the [API usage guidelines](https://aviationweather.gov/data/api/).
- **Privacy.** The app stores nothing and has no accounts. It only sends the airport code you enter to the weather API.

## Deploying

Flask's built-in server is for development only. For a public site, run the app behind a production server such as gunicorn:

```bash
pip install gunicorn
gunicorn app:app
```

## Data source

Weather data comes from the [NOAA Aviation Weather Center](https://aviationweather.gov/data/api/).

## License

[MIT](LICENSE)
