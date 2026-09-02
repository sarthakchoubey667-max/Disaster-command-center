import os
import threading
import time
from datetime import datetime, timedelta, timezone

from requests.auth import HTTPBasicAuth

from services.external_base import request_json, result, unavailable

_token_lock = threading.Lock()
_token_cache = {"access_token": None, "expires_at": 0.0}


def _oauth_token(client_id: str, client_secret: str) -> str:
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"]:
        return _token_cache["access_token"]
    with _token_lock:
        now = time.time()
        if _token_cache["access_token"] and now < _token_cache["expires_at"]:
            return _token_cache["access_token"]
        raw = request_json(
            "POST",
            os.getenv("PLANET_TOKEN_URL", "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"),
            auth=HTTPBasicAuth(client_id, client_secret),
            data={"grant_type": "client_credentials"},
        )
        token = raw["access_token"]
        _token_cache.update(access_token=token, expires_at=now + max(30, int(raw.get("expires_in", 300)) - 30))
        return token


def _oauth_scenes(latitude: float, longitude: float, days: int, limit: int) -> dict:
    client_id = os.getenv("PLANET_CLIENT_ID")
    client_secret = os.getenv("PLANET_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("Planet OAuth credentials are not configured")
    delta = float(os.getenv("PLANET_SEARCH_RADIUS_DEGREES", "0.05"))
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    collection = os.getenv("PLANET_CATALOG_COLLECTION", "sentinel-2-l2a")
    payload = {
        "bbox": [longitude - delta, latitude - delta, longitude + delta, latitude + delta],
        "datetime": f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "collections": [collection],
        "limit": max(1, min(limit, 100)),
    }
    raw = request_json(
        "POST",
        os.getenv("PLANET_CATALOG_URL", "https://services.sentinel-hub.com/catalog/v1/search"),
        headers={"Authorization": f"Bearer {_oauth_token(client_id, client_secret)}"},
        json=payload,
    )
    scenes = []
    for item in raw.get("features", [])[:limit]:
        properties = item.get("properties", {})
        scenes.append({
            "id": item.get("id"),
            "item_type": item.get("collection") or collection,
            "acquired": properties.get("datetime"),
            "cloud_cover": properties.get("eo:cloud_cover"),
            "thumbnail": None,
        })
    return result("Planet", data={"count": len(scenes), "scenes": scenes, "collection": collection}, message="Planet Catalog API (OAuth)")


def _legacy_scenes(key: str, latitude: float, longitude: float, days: int, limit: int) -> dict:
    delta = float(os.getenv("PLANET_SEARCH_RADIUS_DEGREES", "0.05"))
    geometry = {"type": "Polygon", "coordinates": [[[longitude-delta, latitude-delta], [longitude+delta, latitude-delta], [longitude+delta, latitude+delta], [longitude-delta, latitude+delta], [longitude-delta, latitude-delta]]]}
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    payload = {"item_types": [os.getenv("PLANET_ITEM_TYPE", "PSScene")], "filter": {"type": "AndFilter", "config": [{"type": "GeometryFilter", "field_name": "geometry", "config": geometry}, {"type": "DateRangeFilter", "field_name": "acquired", "config": {"gte": start}}]}}
    raw = request_json("POST", os.getenv("PLANET_QUICK_SEARCH_URL", "https://api.planet.com/data/v1/quick-search"), auth=HTTPBasicAuth(key, ""), json=payload, params={"_page_size": limit})
    scenes = [{"id": item.get("id"), "item_type": item.get("properties", {}).get("item_type"), "acquired": item.get("properties", {}).get("acquired"), "cloud_cover": item.get("properties", {}).get("cloud_cover"), "thumbnail": item.get("_links", {}).get("thumbnail")} for item in raw.get("features", [])[:limit]]
    return result("Planet", data={"count": len(scenes), "scenes": scenes}, message="Planet Data API (legacy key)")


def get_satellite_scenes(latitude: float, longitude: float, days: int = 30, limit: int = 10) -> dict:
    has_oauth = bool(os.getenv("PLANET_CLIENT_ID") and os.getenv("PLANET_CLIENT_SECRET"))
    key = os.getenv("PLANET_API_KEY")
    if not has_oauth and not key:
        return unavailable("Planet", "Planet credentials are not configured", {"count": 0, "scenes": []})
    try:
        return _oauth_scenes(latitude, longitude, days, limit) if has_oauth else _legacy_scenes(key, latitude, longitude, days, limit)
    except Exception:
        return unavailable("Planet", "Satellite provider is currently unavailable", {"count": 0, "scenes": []})
