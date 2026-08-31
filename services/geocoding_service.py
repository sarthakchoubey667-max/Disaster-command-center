import os

from services.external_base import request_json, result, unavailable


def geocode(address: str | None = None, latitude: float | None = None, longitude: float | None = None) -> dict:
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        return unavailable("Google Geocoding", "GOOGLE_MAPS_API_KEY is not configured", None)
    params = {"key": key}
    params["address" if address else "latlng"] = address or f"{latitude},{longitude}"
    try:
        raw = request_json("GET", os.getenv("GOOGLE_GEOCODING_API_URL", "https://maps.googleapis.com/maps/api/geocode/json"), params=params)
        if raw.get("status") not in ("OK", "ZERO_RESULTS"):
            raise RuntimeError(raw.get("error_message") or raw.get("status"))
        items = [{"formatted_address": item.get("formatted_address"), "location": item.get("geometry", {}).get("location"), "place_id": item.get("place_id"), "types": item.get("types", [])} for item in raw.get("results", [])]
        return result("Google Geocoding", data={"count": len(items), "results": items})
    except Exception:
        return unavailable("Google Geocoding", "Geocoding provider is currently unavailable", None)
