import os
import threading
import time

from services.external_base import request_json, result, unavailable


_cache = {}
_cache_lock = threading.Lock()
_last_nominatim_request = 0.0


def _cache_key(address, latitude, longitude):
    return (address.strip().lower(), None, None) if address else (None, round(float(latitude), 4), round(float(longitude), 4))


def _cached(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry["expires_at"] > time.monotonic():
            return entry["value"]
    return None


def _store(key, value):
    with _cache_lock:
        _cache[key] = {"value": value, "expires_at": time.monotonic() + int(os.getenv("GEOCODING_CACHE_SECONDS", "86400"))}
    return value


def _google_geocode(key: str, address, latitude, longitude) -> dict:
    params = {"key": key}
    params["address" if address else "latlng"] = address or f"{latitude},{longitude}"
    raw = request_json("GET", os.getenv("GOOGLE_GEOCODING_API_URL", "https://maps.googleapis.com/maps/api/geocode/json"), params=params)
    if raw.get("status") not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(raw.get("error_message") or raw.get("status"))
    items = [{"formatted_address": item.get("formatted_address"), "location": item.get("geometry", {}).get("location"), "place_id": item.get("place_id"), "types": item.get("types", [])} for item in raw.get("results", [])]
    return result("Google Geocoding", data={"count": len(items), "results": items})


def _nominatim_geocode(address, latitude, longitude) -> dict:
    global _last_nominatim_request
    # The public Nominatim policy requires no more than one request per second.
    with _cache_lock:
        delay = 1.0 - (time.monotonic() - _last_nominatim_request)
        if delay > 0:
            time.sleep(delay)
        _last_nominatim_request = time.monotonic()
    headers = {
        "User-Agent": os.getenv("NOMINATIM_USER_AGENT", "DisasterCommandCenter/1.0 (github.com/sarthakchoubey667-max/Disaster-command-center)"),
        "Accept-Language": os.getenv("GEOCODING_LANGUAGE", "en"),
    }
    base_url = os.getenv("NOMINATIM_API_URL", "https://nominatim.openstreetmap.org")
    if address:
        raw = request_json("GET", f"{base_url}/search", headers=headers, params={"q": address, "format": "jsonv2", "limit": 1})
    else:
        item = request_json("GET", f"{base_url}/reverse", headers=headers, params={"lat": latitude, "lon": longitude, "format": "jsonv2", "zoom": 14})
        raw = [item] if item and not item.get("error") else []
    items = []
    for item in raw:
        lat, lon = item.get("lat"), item.get("lon")
        items.append({
            "formatted_address": item.get("display_name"),
            "location": {"lat": float(lat), "lng": float(lon)} if lat is not None and lon is not None else None,
            "place_id": str(item.get("place_id")) if item.get("place_id") is not None else None,
            "types": [item.get("type")] if item.get("type") else [],
        })
    return result("OpenStreetMap Nominatim", data={"count": len(items), "results": items, "attribution": "© OpenStreetMap contributors"}, message="Google Geocoding fallback")


def geocode(address: str | None = None, latitude: float | None = None, longitude: float | None = None) -> dict:
    if not address and (latitude is None or longitude is None):
        return unavailable("Geocoding", "Provide an address or latitude and longitude", None)
    cache_key = _cache_key(address, latitude, longitude)
    cached = _cached(cache_key)
    if cached is not None:
        return cached
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if key:
        try:
            return _store(cache_key, _google_geocode(key, address, latitude, longitude))
        except Exception:
            pass
    try:
        return _store(cache_key, _nominatim_geocode(address, latitude, longitude))
    except Exception:
        return unavailable("Geocoding", "Geocoding providers are currently unavailable", None)
