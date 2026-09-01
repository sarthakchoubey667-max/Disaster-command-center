from concurrent.futures import ThreadPoolExecutor

from services.earthquake_service import get_earthquakes
from services.elevation_service import get_elevation
from services.geocoding_service import geocode
from services.river_service import get_river_data
from services.sachet_service import get_sachet_alerts
from services.satellite_service import get_satellite_scenes
from services.weather_service import get_weather_data


def get_fused_external_data(latitude, longitude, sensor_fallback=None):
    sensors = sensor_fallback or {}
    calls = {
        "weather": lambda: get_weather_data(latitude, longitude, sensors),
        "earthquakes": lambda: get_earthquakes(latitude, longitude),
        "elevation": lambda: get_elevation(latitude, longitude),
        "geocoding": lambda: geocode(latitude=latitude, longitude=longitude),
        "alerts": get_sachet_alerts,
        "river": lambda: get_river_data(latitude, longitude),
        "satellite": lambda: get_satellite_scenes(latitude, longitude),
    }
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = {name: pool.submit(call) for name, call in calls.items()}
        sources = {name: future.result() for name, future in futures.items()}
    available = [name for name, value in sources.items() if value.get("status") == "success"]
    features = _landslide_features(sources, sensors)
    return {
        "status": "success" if available else "fallback",
        "location": {"latitude": latitude, "longitude": longitude},
        "available_sources": available,
        "fallback_sources": [name for name in calls if name not in available],
        "sources": sources,
        "landslide_features": features,
        "operational": _operational_snapshot(sources, sensors, features),
    }


def _landslide_features(sources, sensors):
    weather = sources["weather"].get("data") or {}
    quakes = (sources["earthquakes"].get("data") or {}).get("events", [])
    river = sources["river"].get("data") or {}
    return {
        "rainfall_mm": weather.get("rainfall_1h", sensors.get("rainfall")),
        "humidity_percent": weather.get("humidity", sensors.get("humidity")),
        "temperature_c": weather.get("temperature", sensors.get("temperature")),
        "wind_speed_mps": weather.get("wind_speed", sensors.get("wind_speed")),
        "water_level": river.get("water_level", sensors.get("water_level")),
        "recent_earthquake_count": len(quakes),
        "max_recent_magnitude": max((event.get("magnitude") or 0 for event in quakes), default=0),
        "terrain": sources["elevation"].get("data"),
        "official_alert_count": (sources["alerts"].get("data") or {}).get("count", 0),
        "satellite_scene_count": (sources["satellite"].get("data") or {}).get("count", 0),
    }


def _number(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _risk_level(score):
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MODERATE"
    return "LOW"


def _operational_snapshot(sources, sensors, features):
    """Translate provider-specific responses into app-ready operational data."""
    weather_live = sources["weather"].get("status") == "success"
    river_live = sources["river"].get("status") == "success"
    weather = sources["weather"].get("data") or {}
    river = sources["river"].get("data") or {}

    sensor_values = dict(sensors)
    sensor_sources = {key: "controlled_simulation" for key in sensor_values}
    for target, provider_key in (
        ("rainfall", "rainfall_1h"),
        ("temperature", "temperature"),
        ("humidity", "humidity"),
        ("wind_speed", "wind_speed"),
    ):
        if weather_live and weather.get(provider_key) is not None:
            sensor_values[target] = weather[provider_key]
            sensor_sources[target] = "OpenWeather"
    if river_live:
        for key in ("water_level", "flow_rate"):
            if river.get(key) is not None:
                sensor_values[key] = river[key]
                sensor_sources[key] = "NWDP/NWIC"

    rain_score = min(_number(features.get("rainfall_mm")) / 2.0, 35)
    water_score = min(_number(features.get("water_level")) * 8, 25)
    humidity_score = max(0, min((_number(features.get("humidity_percent")) - 60) * 0.5, 15))
    quake_score = min(_number(features.get("max_recent_magnitude")) * 4, 15)
    # The SACHET feed is nationwide, so alerts are intentionally a small signal
    # until a provider supplies reliable geo-targeting for the selected zone.
    alert_score = min(_number(features.get("official_alert_count")) * 0.25, 5)
    external_score = round(min(rain_score + water_score + humidity_score + quake_score + alert_score, 100), 2)

    official_alerts = (sources["alerts"].get("data") or {}).get("alerts", [])
    earthquakes = (sources["earthquakes"].get("data") or {}).get("events", [])
    return {
        "sensors": sensor_values,
        "sensor_sources": sensor_sources,
        "alerts": official_alerts,
        "earthquakes": earthquakes,
        "risk": {
            "score": external_score,
            "level": _risk_level(external_score),
            "factors": {
                "rainfall": round(rain_score, 2),
                "water_level": round(water_score, 2),
                "humidity": round(humidity_score, 2),
                "earthquakes": round(quake_score, 2),
                "official_alerts": round(alert_score, 2),
            },
        },
        "data_mode": "hybrid" if weather_live or river_live else "controlled_simulation",
    }
