from decoder import decode

KHIO = {
    "icaoId": "KHIO", "reportTime": "2026-10-12T20:00:00.000Z", "temp": 15, "dewp": 5.6,
    "wdir": 0, "wspd": 0, "visib": "10+", "altim": 1017.7,
    "rawOb": "METAR KHIO 121953Z 00000KT 10SM CLR 15/06 A3005", "name": "Portland/Hillsboro Arpt, OR, US",
    "cover": "CLR", "clouds": [], "fltCat": "VFR",
}


def test_clear_calm():
    r = decode(KHIO)
    assert r["headline"] == "Clear skies"
    assert r["temperature"].startswith("59°F")
    assert r["wind"].startswith("Calm")
    assert r["pressure"].startswith("30.05")


def test_wind_south_gusts_and_rain():
    r = decode({**KHIO, "wdir": 180, "wspd": 10, "wgst": 20, "wxString": "-RA",
                "cover": "OVC", "clouds": [{"cover": "OVC", "base": 1500}]})
    assert r["wind"] == "12 mph from the south, gusting to 23 mph"
    assert r["weather"] == ["Light rain"]
    assert r["clouds"] == ["Overcast at 1,500 ft"]


def test_variable_wind_and_thunderstorm():
    r = decode({**KHIO, "wdir": "VRB", "wspd": 4, "wxString": "+TSRA"})
    assert "changing direction" in r["wind"]
    assert r["weather"] == ["Heavy thunderstorm with rain"]
