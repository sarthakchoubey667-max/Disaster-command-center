import csv
import io
import math
import os
import threading
import time
from datetime import datetime

import requests

from services.external_base import DEFAULT_TIMEOUT, request_json, result, unavailable


DEFAULT_ASSAM_CSV_URL = (
    "https://nwdp.nwic.gov.in/dataset/6273c426-32f9-4fdf-b67f-e4e7a46d8554/"
    "resource/847f5630-f231-46c0-922d-0f2f379a5cb8/download/"
    "rwl_tel_hr_assam_999_2026_2030.csv"
)
_cache_lock = threading.Lock()
_cache = {"rows": None, "expires_at": 0.0}


def _normalized(name: str) -> str:
    return "".join(character for character in str(name).lower() if character.isalnum())


def _field(fieldnames: list[str], *needles: str) -> str | None:
    normalized = {name: _normalized(name) for name in fieldnames}
    for needle in needles:
        exact = next((name for name, value in normalized.items() if value == needle), None)
        if exact:
            return exact
    for needle in needles:
        partial = next((name for name, value in normalized.items() if needle in value), None)
        if partial:
            return partial
    return None


def _number(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _timestamp(value: str | None) -> float:
    if not value:
        return 0.0
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        pass
    for pattern in ("%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).timestamp()
        except ValueError:
            continue
    return 0.0


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _csv_rows(url: str) -> list[dict]:
    now = time.time()
    if _cache["rows"] is not None and now < _cache["expires_at"]:
        return _cache["rows"]
    with _cache_lock:
        now = time.time()
        if _cache["rows"] is not None and now < _cache["expires_at"]:
            return _cache["rows"]
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig", errors="replace"))))
        _cache["rows"] = rows
        _cache["expires_at"] = now + int(os.getenv("NWIC_CACHE_SECONDS", "900"))
        return rows


def _public_assam_data(latitude: float, longitude: float) -> dict:
    rows = _csv_rows(os.getenv("NWIC_ASSAM_RIVER_CSV_URL", DEFAULT_ASSAM_CSV_URL))
    if not rows:
        raise ValueError("NWIC dataset contains no rows")
    fields = list(rows[0].keys())
    level_key = _field(fields, "riverwaterlevel", "waterlevel", "rwl")
    if not level_key:
        raise ValueError("NWIC water-level column was not found")
    lat_key = _field(fields, "latitude", "lat")
    lon_key = _field(fields, "longitude", "lon", "lng")
    date_key = _field(fields, "datetime", "observationdatetime", "timestamp", "date")
    station_key = _field(fields, "stationname", "station", "sitename", "site")
    river_key = _field(fields, "rivername", "river")

    candidates = []
    for row in rows:
        level = _number(row.get(level_key))
        if level is None:
            continue
        row_lat = _number(row.get(lat_key)) if lat_key else None
        row_lon = _number(row.get(lon_key)) if lon_key else None
        distance = _distance_km(latitude, longitude, row_lat, row_lon) if row_lat is not None and row_lon is not None else None
        candidates.append((distance if distance is not None else 1e9, -_timestamp(row.get(date_key) if date_key else None), row, level, row_lat, row_lon))
    if not candidates:
        raise ValueError("NWIC dataset contains no usable water-level observations")

    nearest_distance = min(item[0] for item in candidates)
    nearby = [item for item in candidates if item[0] == nearest_distance] if nearest_distance < 1e9 else candidates
    chosen = min(nearby, key=lambda item: item[1])
    distance, _, row, level, row_lat, row_lon = chosen
    station = {
        "name": row.get(station_key) if station_key else "NWIC Assam station",
        "river": row.get(river_key) if river_key else None,
        "latitude": row_lat,
        "longitude": row_lon,
        "water_level": level,
        "observed_at": row.get(date_key) if date_key else None,
        "distance_km": round(distance, 2) if distance < 1e9 else None,
    }
    return result("NWDP/NWIC", data={
        "stations": [station],
        "water_level": level,
        "observed_at": station["observed_at"],
        "nearest_station": station["name"],
        "river": station["river"],
        "distance_km": station["distance_km"],
        "dataset": "Assam River Water Level (Telemetry - Hourly), 2026-2030",
    }, message="Official NWIC open dataset")


def get_river_data(latitude: float, longitude: float) -> dict:
    url = os.getenv("NWIC_API_URL")
    try:
        if not url:
            return _public_assam_data(latitude, longitude)
        headers = {}
        token = os.getenv("NWIC_API_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        raw = request_json("GET", url, headers=headers, params={"lat": latitude, "lon": longitude})
        return result("NWDP/NWIC", data=raw)
    except Exception:
        return unavailable("NWDP/NWIC", "River data provider is currently unavailable", {"stations": [], "water_level": None})
