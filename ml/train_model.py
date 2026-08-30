import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report


# Load dataset
data = pd.read_csv("flood_data.csv")

# Features
X = data[
    [
        "rainfall",
        "water_level",
        "flow_rate",
        "temperature",
        "humidity",
        "wind_speed"
    ]
]

# Target
y = data["flood"]


# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# Create model
model = RandomForestClassifier(
    n_estimators=200,
    random_state=42
)


# Train
model.fit(X_train, y_train)


# Test
predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("--------------------------------")
print("Flood Prediction Model")
print("--------------------------------")

print(f"Accuracy: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(classification_report(y_test, predictions))


# Feature importance
print("\nFeature Importance:")

for feature, importance in zip(
    X.columns,
    model.feature_importances_
):
    print(f"{feature}: {importance:.3f}")


# Save model
joblib.dump(model, "flood_model.pkl")

print("\nModel saved as flood_model.pkl")