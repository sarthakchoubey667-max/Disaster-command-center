import os
from pathlib import Path

import joblib


FEATURE_NAMES = ["rainfall_mm", "humidity_percent", "water_level", "elevation_m", "max_recent_magnitude", "official_alert_count", "field_report_count"]
MODEL_PATH = Path(os.getenv("LANDSLIDE_MODEL_PATH", Path(__file__).resolve().parent.parent / "ml" / "landslide_model.pkl"))
_model = None


def _number(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _load_model():
    global _model
    if _model is None and MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
    return _model


def predict_landslide_risk(features: dict) -> dict:
    values = {
        "rainfall_mm": _number(features.get("rainfall_mm")),
        "humidity_percent": _number(features.get("humidity_percent")),
        "water_level": _number(features.get("water_level")),
        "elevation_m": _number((features.get("terrain") or {}).get("elevation_m")),
        "max_recent_magnitude": _number(features.get("max_recent_magnitude")),
        "official_alert_count": _number(features.get("official_alert_count")),
        "field_report_count": _number(features.get("field_report_count")),
    }
    model = _load_model()
    if model is not None:
        vector = [[values[name] for name in FEATURE_NAMES]]
        probability = float(model.predict_proba(vector)[0][-1]) if hasattr(model, "predict_proba") else float(model.predict(vector)[0])
        score = round(max(0, min(probability * 100, 100)), 2)
        method = "trained_model"
        factors = {name: values[name] for name in FEATURE_NAMES}
    else:
        factors = {
            "rainfall": min(values["rainfall_mm"] / 2.0, 30),
            "humidity": max(0, min((values["humidity_percent"] - 60) * 0.4, 12)),
            "water_level": min(values["water_level"] * 0.35, 18),
            "terrain": min(values["elevation_m"] / 80, 10),
            "earthquakes": min(values["max_recent_magnitude"] * 3, 12),
            "official_alerts": min(values["official_alert_count"] * 0.2, 4),
            "field_reports": min(values["field_report_count"] * 7, 14),
        }
        score = round(min(sum(factors.values()), 100), 2)
        method = "transparent_heuristic_fallback"
    level = "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MODERATE" if score >= 35 else "LOW"
    return {"score": score, "level": level, "method": method, "model_loaded": model is not None, "factors": {key: round(value, 2) for key, value in factors.items()}}
