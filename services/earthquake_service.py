import os
from datetime import datetime, timedelta, timezone

from services.external_base import request_json, result, unavailable


def get_earthquakes(latitude: float, longitude: float, radius_km: float = 250, days: int = 7, limit: int = 25) -> dict:
    start = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    try:
        raw = request_json("GET", os.getenv("USGS_API_URL", "https://earthquake.usgs.gov/fdsnws/event/1/query"), params={"format": "geojson", "latitude": latitude, "longitude": longitude, "maxradiuskm": radius_km, "starttime": start, "orderby": "time", "limit": limit})
        events = []
        for feature in raw.get("features", []):
            props, coords = feature.get("properties", {}), feature.get("geometry", {}).get("coordinates", [])
            events.append({"id": feature.get("id"), "magnitude": props.get("mag"), "place": props.get("place"), "time_ms": props.get("time"), "url": props.get("url"), "longitude": coords[0] if len(coords) > 0 else None, "latitude": coords[1] if len(coords) > 1 else None, "depth_km": coords[2] if len(coords) > 2 else None})
        return result("USGS", data={"count": len(events), "events": events, "radius_km": radius_km, "days": days})
    except Exception:
        return unavailable("USGS", "Earthquake provider is currently unavailable", {"count": 0, "events": []})
