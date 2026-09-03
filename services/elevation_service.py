import os
import requests
from threading import Lock
from time import monotonic

from services.external_base import DEFAULT_TIMEOUT, result, unavailable


_cache = {}
_cache_lock = Lock()


def _cache_key(latitude: float, longitude: float) -> tuple[float, float]:
    return round(latitude, 4), round(longitude, 4)


def _cached(latitude: float, longitude: float):
    key = _cache_key(latitude, longitude)
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry["expires_at"] > monotonic():
            return entry["value"]
    return None


def _store(latitude: float, longitude: float, value: dict, ttl_seconds: float):
    key = _cache_key(latitude, longitude)
    with _cache_lock:
        _cache[key] = {
            "value": value,
            "expires_at": monotonic() + ttl_seconds,
        }
    return value


def _open_meteo_elevation(latitude: float, longitude: float) -> dict:
    response = requests.get(
        os.getenv("OPEN_METEO_ELEVATION_URL", "https://api.open-meteo.com/v1/elevation"),
        timeout=DEFAULT_TIMEOUT,
        params={"latitude": latitude, "longitude": longitude},
    )
    response.raise_for_status()
    elevations = response.json().get("elevation") or []
    if not elevations:
        raise ValueError("Open-Meteo response did not contain elevation")
    return _store(latitude, longitude, result(
        "Open-Meteo Elevation",
        data={
            "elevation_m": round(float(elevations[0]), 2),
            "sample_count": 1,
            "dem_type": "Copernicus DEM GLO-90",
            "method": "open_meteo_fallback",
            "attribution": "Copernicus DEM via Open-Meteo",
        },
        message="OpenTopography fallback",
    ), float(os.getenv("OPENTOPOGRAPHY_CACHE_SECONDS", "43200")))


def get_elevation(latitude: float, longitude: float) -> dict:
    cached = _cached(latitude, longitude)
    if cached is not None:
        return cached

    key = os.getenv("OPENTOPOGRAPHY_API_KEY")
    if not key:
        try:
            return _open_meteo_elevation(latitude, longitude)
        except Exception:
            return unavailable("Elevation", "Elevation providers are currently unavailable", {"elevation_m": None})
    dataset = os.getenv("OPENTOPOGRAPHY_POINT_DATASET", "COP30")
    point_url = os.getenv(
        "OPENTOPOGRAPHY_POINT_API_URL",
        "https://portal.opentopography.org/API/v1/elevation",
    )
    try:
        response = requests.get(
            point_url,
            timeout=DEFAULT_TIMEOUT,
            params={
                "longitude": longitude,
                "latitude": latitude,
                "dataset": dataset,
                "API_Key": key,
            },
        )
        response.raise_for_status()
        payload = response.json()
        elevation = payload.get("Elevation", payload.get("elevation"))
        if elevation is None and isinstance(payload.get("data"), dict):
            elevation = payload["data"].get("elevation")
        if elevation is None:
            raise ValueError("Point elevation response did not contain elevation")
        return _store(latitude, longitude, result(
            "OpenTopography",
            data={
                "elevation_m": round(float(elevation), 2),
                "sample_count": 1,
                "dem_type": dataset,
                "method": "point_elevation",
            },
        ), float(os.getenv("OPENTOPOGRAPHY_CACHE_SECONDS", "43200")))
    except Exception:
        # Preserve compatibility with the established global DEM API when the
        # point service is unavailable or an older account cannot access it.
        try:
            response = requests.get(
                os.getenv(
                    "OPENTOPOGRAPHY_API_URL",
                    "https://portal.opentopography.org/API/globaldem",
                ),
                timeout=DEFAULT_TIMEOUT,
                params={
                    "demtype": os.getenv("OPENTOPOGRAPHY_DEM_TYPE", "SRTMGL1"),
                    "south": latitude - 0.001,
                    "north": latitude + 0.001,
                    "west": longitude - 0.001,
                    "east": longitude + 0.001,
                    "outputFormat": "AAIGrid",
                    "API_Key": key,
                },
            )
            response.raise_for_status()
            rows = [
                line.split()
                for line in response.text.splitlines()
                if line
                and not line.lower().startswith(
                    ("ncols", "nrows", "xll", "yll", "cellsize", "nodata")
                )
            ]
            values = [
                float(value)
                for row in rows
                for value in row
                if value != "-9999"
            ]
            elevation = round(sum(values) / len(values), 2) if values else None
            if elevation is None:
                raise ValueError("DEM response did not contain elevation")
            return _store(latitude, longitude, result(
                "OpenTopography",
                data={
                    "elevation_m": elevation,
                    "sample_count": len(values),
                    "dem_type": os.getenv("OPENTOPOGRAPHY_DEM_TYPE", "SRTMGL1"),
                    "method": "global_dem",
                },
            ), float(os.getenv("OPENTOPOGRAPHY_CACHE_SECONDS", "43200")))
        except Exception:
            try:
                return _open_meteo_elevation(latitude, longitude)
            except Exception:
                return _store(latitude, longitude, unavailable(
                    "Elevation",
                    "Elevation providers are currently unavailable",
                    {"elevation_m": None},
                ), float(os.getenv("OPENTOPOGRAPHY_FAILURE_CACHE_SECONDS", "1800")))
