import os

from services.external_base import request_json, result, unavailable


def get_river_data(latitude: float, longitude: float) -> dict:
    url = os.getenv("NWIC_API_URL")
    if not url:
        return unavailable("NWDP/NWIC", "NWIC_API_URL is not configured; access may require NWIC approval", {"stations": [], "water_level": None})
    headers = {}
    token = os.getenv("NWIC_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        raw = request_json("GET", url, headers=headers, params={"lat": latitude, "lon": longitude})
        return result("NWDP/NWIC", data=raw)
    except Exception:
        return unavailable("NWDP/NWIC", "River data provider is currently unavailable", {"stations": [], "water_level": None})
