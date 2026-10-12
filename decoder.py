"""Turn an aviationweather.gov METAR record into plain English."""
from datetime import datetime

COVER = {
    "CLR": "clear skies",
    "SKC": "clear skies",
    "CAVOK": "clear skies",
    "FEW": "a few clouds",
    "SCT": "scattered clouds",
    "BKN": "mostly cloudy",
    "OVC": "overcast",
    "OVX": "the sky is obscured",
    "VV": "the sky is obscured",
}

# Weather phenomena codes, in the order they can appear in a group like "-TSRA".
INTENSITY = {"-": "light", "+": "heavy"}
DESCRIPTOR = {
    "MI": "shallow", "BC": "patchy", "PR": "partial", "DR": "drifting",
    "BL": "blowing", "SH": "showers of", "TS": "thunderstorm with",
    "FZ": "freezing",
}
PHENOMENA = {
    "DZ": "drizzle", "RA": "rain", "SN": "snow", "SG": "snow grains",
    "IC": "ice crystals", "PL": "ice pellets", "GR": "hail", "GS": "small hail",
    "UP": "unknown precipitation", "BR": "mist", "FG": "fog", "FU": "smoke",
    "VA": "volcanic ash", "DU": "dust", "SA": "sand", "HZ": "haze",
    "PY": "spray", "PO": "dust whirls", "SQ": "squalls", "FC": "a funnel cloud",
    "SS": "a sandstorm", "DS": "a duststorm",
}

CARDINALS = [
    "north", "north-northeast", "northeast", "east-northeast",
    "east", "east-southeast", "southeast", "south-southeast",
    "south", "south-southwest", "southwest", "west-southwest",
    "west", "west-northwest", "northwest", "north-northwest",
]

FLIGHT_CATEGORY = {
    "VFR": "Good flying conditions (VFR).",
    "MVFR": "Marginal flying conditions (MVFR).",
    "IFR": "Poor visibility for flying (IFR).",
    "LIFR": "Very poor visibility for flying (LIFR).",
}


def c_to_f(c):
    return c * 9 / 5 + 32


def kt_to_mph(kt):
    return kt * 1.15078


def cardinal(degrees):
    return CARDINALS[round(degrees / 22.5) % 16]


def describe_temperature(temp_c):
    f = c_to_f(temp_c)
    if f < 20:
        feel = "freezing cold"
    elif f < 40:
        feel = "cold"
    elif f < 55:
        feel = "cool"
    elif f < 70:
        feel = "mild"
    elif f < 85:
        feel = "warm"
    elif f < 95:
        feel = "hot"
    else:
        feel = "very hot"
    return f"{round(f)}°F ({round(temp_c)}°C), {feel}"


def describe_wind(wdir, wspd, wgst):
    if not wspd:
        return "Calm, with little or no wind"
    mph = round(kt_to_mph(wspd))
    if wdir == "VRB" or wdir is None:
        text = f"{mph} mph from a changing direction"
    else:
        text = f"{mph} mph from the {cardinal(int(wdir))}"
    if wgst:
        text += f", gusting to {round(kt_to_mph(wgst))} mph"
    return text


def parse_miles(visib):
    """Convert an API visibility value to miles, or None if it can't be read.

    Handles numbers, '10+', and fractions such as '1/4' or '1 1/2'.
    """
    if isinstance(visib, (int, float)):
        return float(visib)
    try:
        total = 0.0
        for part in str(visib).rstrip("+").split():
            if "/" in part:
                num, den = part.split("/")
                total += float(num) / float(den)
            else:
                total += float(part)
        return total
    except (ValueError, ZeroDivisionError):
        return None


def describe_visibility(visib):
    if visib is None:
        return None
    miles = parse_miles(visib)
    if miles is None:
        return None
    if isinstance(visib, str) and visib.endswith("+"):
        return f"{miles:g}+ miles, excellent visibility"
    label = "excellent" if miles >= 10 else "good" if miles >= 5 else "reduced" if miles >= 3 else "poor"
    unit = "mile" if miles == 1 else "miles"
    return f"{miles:g} {unit}, {label} visibility"


def describe_weather(wx_string):
    """Decode a present-weather string such as '-RA BR' or 'TSRA'."""
    if not wx_string:
        return []
    results = []
    for group in wx_string.split():
        intensity = ""
        if group[0] in INTENSITY:
            intensity = INTENSITY[group[0]] + " "
            group = group[1:]
        vicinity = group.startswith("VC")
        if vicinity:
            group = group[2:]
        words = []
        while len(group) >= 2:
            code, group = group[:2], group[2:]
            if code in DESCRIPTOR:
                words.append(DESCRIPTOR[code])
            elif code in PHENOMENA:
                words.append(PHENOMENA[code])
            else:
                words.append(code)
        # A descriptor with no phenomenon after it (VCSH, TS) reads awkwardly
        # as "showers of" or "thunderstorm with", so drop the dangling word.
        if words and words[-1] in ("showers of", "thunderstorm with"):
            words[-1] = words[-1].rsplit(" ", 1)[0]
        text = intensity + " ".join(words)
        if vicinity:
            text += " nearby"
        results.append(text.strip().capitalize())
    return results


def describe_clouds(clouds, cover):
    layers = []
    for layer in clouds or []:
        name = COVER.get(layer.get("cover"), layer.get("cover"))
        base = layer.get("base")
        if base:
            layers.append(f"{name.capitalize()} at {base:,} ft")
        else:
            layers.append(name.capitalize())
    if not layers and cover:
        layers.append(COVER.get(cover, cover).capitalize())
    return layers


def sky_summary(clouds, cover, wx):
    """One-line headline for the report."""
    if wx:
        return wx[0]
    top = cover or (clouds[-1].get("cover") if clouds else None)
    if clouds:
        order = ["FEW", "SCT", "BKN", "OVC", "OVX", "VV"]
        covers = [c.get("cover") for c in clouds if c.get("cover") in order]
        if covers:
            top = max(covers, key=order.index)
    text = COVER.get(top, "unknown sky conditions")
    return text.capitalize()


def format_time(iso):
    """'2026-10-12T23:00:00.000Z' -> '23:00 UTC on Oct 12, 2026'."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    return f"{dt:%H:%M} UTC on {dt:%b} {dt.day}, {dt.year}"


def decode(record):
    """Return a dict of friendly strings for one API record."""
    wx = describe_weather(record.get("wxString"))
    clouds = describe_clouds(record.get("clouds"), record.get("cover"))
    result = {
        "station": record.get("icaoId"),
        "name": record.get("name"),
        "raw": record.get("rawOb"),
        "headline": sky_summary(record.get("clouds"), record.get("cover"), wx),
        "temperature": None,
        "dewpoint": None,
        "wind": describe_wind(record.get("wdir"), record.get("wspd"), record.get("wgst")),
        "visibility": describe_visibility(record.get("visib")),
        "pressure": None,
        "weather": wx,
        "clouds": clouds,
        "flight_category": FLIGHT_CATEGORY.get(record.get("fltCat")),
        "observed": format_time(record.get("reportTime")),
    }
    if record.get("temp") is not None:
        result["temperature"] = describe_temperature(record["temp"])
    if record.get("dewp") is not None:
        f = c_to_f(record["dewp"])
        result["dewpoint"] = f"{round(f)}°F ({round(record['dewp'])}°C)"
    if record.get("altim") is not None:
        result["pressure"] = f"{record['altim'] * 0.02953:.2f} inHg ({round(record['altim'])} hPa)"
    result["summary"] = build_sentence(result, record)
    return result


def build_sentence(result, record):
    parts = [result["headline"]]
    if record.get("temp") is not None:
        parts.append(f"{round(c_to_f(record['temp']))} degrees")
    wind = result["wind"]
    parts.append(wind[0].lower() + wind[1:] if wind.startswith("Calm") else f"wind {wind}")
    return ", ".join(parts) + "."
