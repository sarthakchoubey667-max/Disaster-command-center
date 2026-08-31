import os

from services.external_base import request_json, result, unavailable


def get_weather_data(latitude: float, longitude: float, fallback: dict | None = None) -> dict:
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        return unavailable("OpenWeather", "OPENWEATHER_API_KEY is not configured", fallback)
    try:
        raw = request_json("GET", os.getenv("OPENWEATHER_API_URL", "https://api.openweathermap.org/data/2.5/weather"), params={"lat": latitude, "lon": longitude, "appid": key, "units": "metric"})
        rain = raw.get("rain", {})
        return result("OpenWeather", data={
            "temperature": raw.get("main", {}).get("temp"),
            "humidity": raw.get("main", {}).get("humidity"),
            "pressure": raw.get("main", {}).get("pressure"),
            "wind_speed": raw.get("wind", {}).get("speed"),
            "rainfall_1h": rain.get("1h", 0),
            "rainfall_3h": rain.get("3h", 0),
            "cloud_cover": raw.get("clouds", {}).get("all"),
            "description": (raw.get("weather") or [{}])[0].get("description"),
            "location_name": raw.get("name"),
        })
    except Exception:
        return unavailable("OpenWeather", "Weather provider is currently unavailable", fallback)
