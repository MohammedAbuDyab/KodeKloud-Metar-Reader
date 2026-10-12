"""METAR Reader: a small Flask app that shows airport weather in plain English.

The user enters an airport code, the app fetches the latest METAR report from
the aviationweather.gov API, and ``decoder.decode`` turns it into readable text.

Run locally with ``python app.py``. Set ``FLASK_DEBUG=1`` for debug mode during
development. Never enable debug mode on a public server.
"""

import re
from typing import Any, Optional

import requests
from flask import Flask, render_template, request

from decoder import decode

# Public, keyless endpoint from the U.S. Aviation Weather Center.
API_URL = "https://aviationweather.gov/api/data/metar"

# Seconds to wait for the weather API before giving up.
REQUEST_TIMEOUT = 10

# Airport identifiers are 3 or 4 letters or digits (for example HIO or KHIO).
# Checking this before calling the API keeps junk input out of the request.
STATION_RE = re.compile(r"^[A-Z0-9]{3,4}$")

app = Flask(__name__)


def fetch_metar(code: str) -> Optional[dict[str, Any]]:
    """Fetch the newest METAR record for an airport.

    Args:
        code: A 4-character ICAO airport code, such as ``"KHIO"``.

    Returns:
        The API's JSON record for the station, or ``None`` if the API has no
        report for that code.

    Raises:
        requests.RequestException: If the request fails, times out, or the API
            returns an error status.
    """
    response = requests.get(
        API_URL,
        params={"ids": code, "format": "json"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    # The API returns an empty body (not an empty list) for unknown stations.
    if not response.content.strip():
        return None

    records = response.json()
    return records[0] if records else None


@app.route("/")
def index() -> str:
    """Show the landing page with the airport code form."""
    return render_template("index.html", code="", error=None)


@app.route("/metar", methods=["GET", "POST"])
def metar() -> tuple[str, int] | str:
    """Look up an airport and show its decoded weather report.

    Accepts the code from a form post or a query string (``?code=KHIO``). On
    success it renders the report page. On failure it re-renders the landing
    page with an error message and an appropriate HTTP status.
    """
    code = (request.values.get("code") or "").strip().upper()

    if not STATION_RE.match(code):
        error = "Airport codes are 3 or 4 letters, like KHIO or HIO."
        return render_template("index.html", code=code, error=error), 400

    # US airports can be typed without the leading K (HIO -> KHIO).
    station = code if len(code) == 4 else f"K{code}"

    try:
        record = fetch_metar(station)
    except requests.RequestException:
        error = "The weather service isn't responding right now. Try again in a minute."
        return render_template("index.html", code=code, error=error), 502

    if record is None:
        error = f"No weather report found for {code}. Check the code and try again."
        return render_template("index.html", code=code, error=error), 404

    return render_template("result.html", report=decode(record))


if __name__ == "__main__":
    # Debug mode is off unless FLASK_DEBUG=1 is set in the environment.
    app.run()
