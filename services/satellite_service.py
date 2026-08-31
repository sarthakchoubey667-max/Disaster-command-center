import os
from datetime import datetime, timedelta, timezone

from requests.auth import HTTPBasicAuth

from services.external_base import request_json, result, unavailable


def get_satellite_scenes(latitude: float, longitude: float, days: int = 30, limit: int = 10) -> dict:
    key = os.getenv("PLANET_API_KEY")
    if not key:
        return unavailable("Planet", "PLANET_API_KEY is not configured", {"count": 0, "scenes": []})
    delta = float(os.getenv("PLANET_SEARCH_RADIUS_DEGREES", "0.05"))
    geometry = {"type": "Polygon", "coordinates": [[[longitude-delta, latitude-delta], [longitude+delta, latitude-delta], [longitude+delta, latitude+delta], [longitude-delta, latitude+delta], [longitude-delta, latitude-delta]]]}
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    payload = {"item_types": [os.getenv("PLANET_ITEM_TYPE", "PSScene")], "filter": {"type": "AndFilter", "config": [{"type": "GeometryFilter", "field_name": "geometry", "config": geometry}, {"type": "DateRangeFilter", "field_name": "acquired", "config": {"gte": start}}]}}
    try:
        raw = request_json("POST", os.getenv("PLANET_QUICK_SEARCH_URL", "https://api.planet.com/data/v1/quick-search"), auth=HTTPBasicAuth(key, ""), json=payload, params={"_page_size": limit})
        scenes = [{"id": item.get("id"), "item_type": item.get("properties", {}).get("item_type"), "acquired": item.get("properties", {}).get("acquired"), "cloud_cover": item.get("properties", {}).get("cloud_cover"), "thumbnail": item.get("_links", {}).get("thumbnail")} for item in raw.get("features", [])[:limit]]
        return result("Planet", data={"count": len(scenes), "scenes": scenes})
    except Exception:
        return unavailable("Planet", "Satellite provider is currently unavailable", {"count": 0, "scenes": []})
