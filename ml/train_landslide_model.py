"""Train an optional landslide classifier from a verified historical CSV."""
import argparse
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

FEATURES = ["rainfall_mm", "humidity_percent", "water_level", "elevation_m", "max_recent_magnitude", "official_alert_count", "field_report_count"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="Verified historical CSV with feature columns and landslide_event target")
    parser.add_argument("--output", default=str(Path(__file__).with_name("landslide_model.pkl")))
    args = parser.parse_args()
    data = np.genfromtxt(args.csv, delimiter=",", names=True, dtype=None, encoding="utf-8")
    missing = [name for name in [*FEATURES, "landslide_event"] if name not in (data.dtype.names or ())]
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(missing)}")
    x = np.column_stack([data[name].astype(float) for name in FEATURES])
    y = data["landslide_event"].astype(int)
    if len(set(y.tolist())) < 2:
        raise ValueError("Training data must include both landslide and non-landslide examples")
    model = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42, min_samples_leaf=2)
    model.fit(x, y)
    joblib.dump(model, args.output)
    print(f"Saved landslide model to {args.output} using {len(y)} verified records")


if __name__ == "__main__":
    main()
