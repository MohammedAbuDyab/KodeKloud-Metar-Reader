import re

import requests
from flask import Flask, render_template, request

from decoder import decode

API_URL = "https://aviationweather.gov/api/data/metar"
STATION_RE = re.compile(r"^[A-Za-z0-9]{3,4}$")

app = Flask(__name__)


def fetch_metar(code):
    """Return the newest METAR record for an airport code, or None if there isn't one."""
    resp = requests.get(API_URL, params={"ids": code, "format": "json"}, timeout=10)
    resp.raise_for_status()
    if not resp.content.strip():
        return None
    data = resp.json()
    return data[0] if data else None


@app.route("/")
def index():
    return render_template("index.html", code="", error=None)


@app.route("/metar", methods=["GET", "POST"])
def metar():
    code = (request.values.get("code") or "").strip().upper()
    error = None
    # Allow US airports typed without the leading K, e.g. "HIO".
    if not STATION_RE.match(code):
        error = "Airport codes are 3 or 4 letters, like KHIO or HIO."
    else:
        try:
            record = fetch_metar(code if len(code) == 4 else "K" + code)
            if record is None:
                error = f"No weather report found for {code}. Check the code and try again."
            else:
                return render_template("result.html", report=decode(record))
        except requests.RequestException:
            error = "The weather service isn't responding right now. Try again in a minute."
    return render_template("index.html", code=code, error=error), 400 if error and "3 or 4" in error else 200


if __name__ == "__main__":
    app.run(debug=True)
