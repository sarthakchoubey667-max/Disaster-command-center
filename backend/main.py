from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Iterator, Mapping, Optional

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.imd_service import get_imd_data
from services.sensor_service import (
    get_latest_sensor_data,
    get_sensor_history,
    update_from_imd,
    update_sensor_data,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("DisasterAI")


# ============================================================
# PATHS / MODEL
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "flood_model.pkl"


if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"ML model not found at: {MODEL_PATH}"
    )


try:
    model = joblib.load(MODEL_PATH)
    logger.info("Flood prediction model loaded successfully.")
except Exception as exc:
    logger.exception("Failed to load flood prediction model.")
    raise RuntimeError(
        f"Could not load ML model: {exc}"
    ) from exc


# ============================================================
# GLOBAL CONFIGURATION
# ============================================================

SIMULATION_INTERVAL_SECONDS = 5

MAX_SENSOR_HISTORY = 10
MAX_RISK_HISTORY = 10
MAX_RISK_LOG = 20


# ============================================================
# GLOBAL STATE
# ============================================================

state_lock = RLock()

simulation_step = 0

risk_history: list[float] = []

risk_history_log: list[dict] = []

latest_ai_snapshot: Optional[dict] = None

latest_sensor_data: dict = {
    "water_level": 2.0,
    "rainfall": 80.0,
    "flow_rate": 60.0,
    "temperature": 28.0,
    "humidity": 75.0,
    "wind_speed": 15.0,
    "simulation_phase": "NORMAL",
    "simulation_step": 0,
}


background_task: Optional[asyncio.Task] = None


# ============================================================
# STANDARD RESULT CONTAINER
# ============================================================

class Result(Mapping):
    """
    Standard response container that behaves like a
    read-only mapping.
    """

    def __init__(
        self,
        data=None,
        *,
        status="success",
        error=None,
    ):
        self.status = status
        self.error = error
        self.data = dict(data or {})

    def __getitem__(self, key):
        if key == "status":
            return self.status

        if key == "error":
            return self.error

        if key == "data":
            return self.data

        return self.data[key]

    def __iter__(self) -> Iterator:
        yield "status"
        yield "error"
        yield "data"
        yield from self.data

    def __len__(self):
        return len(self.data) + 3

    def to_dict(self):
        return {
            "status": self.status,
            "error": self.error,
            "data": self.data.copy(),
        }

    @property
    def ok(self):
        return (
            self.status == "success"
            and self.error is None
        )


# ============================================================
# SENSOR INPUT MODEL
# ============================================================

class SensorData(BaseModel):
    water_level: float = Field(
        ...,
        ge=0,
        le=10,
    )

    rainfall: float = Field(
        ...,
        ge=0,
        le=1000,
    )

    flow_rate: float = Field(
        ...,
        ge=0,
        le=500,
    )


# ============================================================
# CONTROLLED SENSOR SIMULATION
# ============================================================

def generate_controlled_sensor_data() -> dict:
    """
    Predictable sensor simulation.

    0 - 4   NORMAL
    5 - 9   RISING
    10 - 14 HIGH_RISK
    15 - 19 CRITICAL

    The cycle repeats continuously.
    """

    global simulation_step

    phase_step = simulation_step % 20

    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    if phase_step <= 4:

        water_level = (
            2.0
            + (phase_step * 0.05)
        )

        rainfall = (
            70
            + (phase_step * 5)
        )

        flow_rate = (
            55
            + (phase_step * 3)
        )

        phase = "NORMAL"

    # --------------------------------------------------------
    # RISING
    # --------------------------------------------------------

    elif phase_step <= 9:

        local_step = phase_step - 5

        water_level = (
            2.3
            + (local_step * 0.18)
        )

        rainfall = (
            100
            + (local_step * 12)
        )

        flow_rate = (
            70
            + (local_step * 7)
        )

        phase = "RISING"

    # --------------------------------------------------------
    # HIGH RISK
    # --------------------------------------------------------

    elif phase_step <= 14:

        local_step = phase_step - 10

        water_level = (
            3.1
            + (local_step * 0.20)
        )

        rainfall = (
            160
            + (local_step * 15)
        )

        flow_rate = (
            105
            + (local_step * 10)
        )

        phase = "HIGH_RISK"

    # --------------------------------------------------------
    # CRITICAL
    # --------------------------------------------------------

    else:

        local_step = phase_step - 15

        water_level = (
            4.1
            + (local_step * 0.15)
        )

        rainfall = (
            230
            + (local_step * 12)
        )

        flow_rate = (
            150
            + (local_step * 8)
        )

        phase = "CRITICAL"

    simulation_step += 1

    return {
        "water_level": round(
            water_level,
            2,
        ),
        "rainfall": round(
            rainfall,
            1,
        ),
        "flow_rate": round(
            flow_rate,
            1,
        ),
        "temperature": 28.0,
        "humidity": 80.0,
        "wind_speed": 15.0,
        "simulation_phase": phase,
        "simulation_step": simulation_step,
    }


# ============================================================
# SENSOR RELIABILITY
# ============================================================

def calculate_sensor_reliability(
    water_level: float,
    rainfall: float,
    flow_rate: float,
) -> dict:

    reliability_scores = {}

    # Water
    if 0 <= water_level <= 5:
        water_score = 100
    elif 5 < water_level <= 6:
        water_score = 60
    else:
        water_score = 20

    # Rainfall
    if 0 <= rainfall <= 300:
        rainfall_score = 100
    elif 300 < rainfall <= 400:
        rainfall_score = 60
    else:
        rainfall_score = 20

    # Flow
    if 0 <= flow_rate <= 200:
        flow_score = 100
    elif 200 < flow_rate <= 300:
        flow_score = 60
    else:
        flow_score = 20

    reliability_scores["water_level"] = water_score
    reliability_scores["rainfall"] = rainfall_score
    reliability_scores["flow_rate"] = flow_score

    overall_reliability = round(
        (
            water_score
            + rainfall_score
            + flow_score
        ) / 3,
        2,
    )

    return {
        "sensor_reliability": reliability_scores,
        "overall_reliability": overall_reliability,
    }


# ============================================================
# SENSOR ANOMALY DETECTION
# ============================================================

def detect_sensor_anomalies(
    current_data: dict,
) -> dict:

    anomalies = {}

    history = get_sensor_history()

    for sensor, current_value in current_data.items():

        if sensor not in (
            "water_level",
            "rainfall",
            "flow_rate",
        ):
            continue

        if len(history) < 3:

            anomalies[sensor] = {
                "anomaly": False,
                "change_percent": 0,
            }

            continue

        previous_values = [
            item.get(sensor, 0)
            for item in history[-3:]
        ]

        average_previous = (
            sum(previous_values)
            / len(previous_values)
        )

        if average_previous == 0:

            change_percent = 0

        else:

            change_percent = (
                abs(
                    (
                        current_value
                        - average_previous
                    )
                    / average_previous
                )
                * 100
            )

        is_anomaly = change_percent > 40

        anomalies[sensor] = {
            "anomaly": is_anomaly,
            "change_percent": round(
                change_percent,
                2,
            ),
        }

    return anomalies


# ============================================================
# SENSOR FUSION
# ============================================================

def calculate_sensor_fusion(
    sensor_data: dict,
    reliability_data: dict,
) -> dict:

    water_weight = (
        reliability_data["water_level"]
        / 100
    )

    rainfall_weight = (
        reliability_data["rainfall"]
        / 100
    )

    flow_weight = (
        reliability_data["flow_rate"]
        / 100
    )

    total_weight = (
        water_weight
        + rainfall_weight
        + flow_weight
    )

    if total_weight == 0:

        return {
            "fused_environmental_score": 0,
            "sensor_weights": {},
        }

    water_normalized = min(
        (
            sensor_data["water_level"]
            / 5
        )
        * 100,
        100,
    )

    rainfall_normalized = min(
        (
            sensor_data["rainfall"]
            / 300
        )
        * 100,
        100,
    )

    flow_normalized = min(
        (
            sensor_data["flow_rate"]
            / 200
        )
        * 100,
        100,
    )

    fused_score = (
        water_normalized
        * water_weight
        + rainfall_normalized
        * rainfall_weight
        + flow_normalized
        * flow_weight
    ) / total_weight

    return {
        "fused_environmental_score": round(
            fused_score,
            2,
        ),
        "sensor_weights": {
            "water_level": round(
                water_weight,
                3,
            ),
            "rainfall": round(
                rainfall_weight,
                3,
            ),
            "flow_rate": round(
                flow_weight,
                3,
            ),
        },
    }


# ============================================================
# TEMPORAL RISK
# ============================================================

def calculate_temporal_risk() -> dict:

    history = get_sensor_history()

    if len(history) < 3:

        return {
            "temporal_score": 0,
            "risk_direction": "INSUFFICIENT_DATA",
            "persistence": len(history),
            "persistence_percentage": round(
                (
                    len(history)
                    / 5
                )
                * 100,
                2,
            ),
        }

    recent = history[-5:]

    avg_water = (
        sum(
            item["water_level"]
            for item in recent
        )
        / len(recent)
    )

    avg_rainfall = (
        sum(
            item["rainfall"]
            for item in recent
        )
        / len(recent)
    )

    avg_flow = (
        sum(
            item["flow_rate"]
            for item in recent
        )
        / len(recent)
    )

    current = recent[-1]

    water_change = (
        current["water_level"]
        - avg_water
    )

    rainfall_change = (
        current["rainfall"]
        - avg_rainfall
    )

    flow_change = (
        current["flow_rate"]
        - avg_flow
    )

    dangerous_readings = 0

    for item in recent:

        danger_signals = 0

        if item["water_level"] >= 3.5:
            danger_signals += 1

        if item["rainfall"] >= 150:
            danger_signals += 1

        if item["flow_rate"] >= 100:
            danger_signals += 1

        if danger_signals >= 2:
            dangerous_readings += 1

    persistence_percentage = round(
        (
            dangerous_readings
            / len(recent)
        )
        * 100,
        2,
    )

    temporal_score = 0

    if persistence_percentage >= 80:
        temporal_score += 40

    elif persistence_percentage >= 60:
        temporal_score += 30

    elif persistence_percentage >= 40:
        temporal_score += 20

    elif persistence_percentage >= 20:
        temporal_score += 10

    if avg_water >= 3.5:
        temporal_score += 20

    if avg_rainfall >= 150:
        temporal_score += 20

    if avg_flow >= 100:
        temporal_score += 10

    if water_change > 0.3:
        temporal_score += 5

    if rainfall_change > 20:
        temporal_score += 5

    if flow_change > 15:
        temporal_score += 5

    temporal_score = min(
        round(
            temporal_score,
            2,
        ),
        100,
    )

    rising_signals = 0
    falling_signals = 0

    if water_change > 0.3:
        rising_signals += 1

    elif water_change < -0.3:
        falling_signals += 1

    if rainfall_change > 20:
        rising_signals += 1

    elif rainfall_change < -20:
        falling_signals += 1

    if flow_change > 15:
        rising_signals += 1

    elif flow_change < -15:
        falling_signals += 1

    if rising_signals > falling_signals:
        risk_direction = "RISING"

    elif falling_signals > rising_signals:
        risk_direction = "FALLING"

    else:
        risk_direction = "STABLE"

    return {
        "temporal_score": temporal_score,
        "risk_direction": risk_direction,
        "persistence": len(recent),
        "persistence_percentage": persistence_percentage,
    }


# ============================================================
# RISK TREND
# ============================================================

def calculate_risk_trend(
    current_risk: float,
    *,
    append: bool = True,
) -> dict:

    previous_risk = None
    trend = "STABLE"
    change = 0

    if risk_history:

        previous_risk = risk_history[-1]

        change = round(
            current_risk
            - previous_risk,
            2,
        )

        if change >= 5:
            trend = "RISING"

        elif change <= -5:
            trend = "FALLING"

        else:
            trend = "STABLE"

    if append:

        risk_history.append(
            current_risk
        )

        if len(risk_history) > MAX_RISK_HISTORY:
            risk_history.pop(0)

    return {
        "previous_risk": previous_risk,
        "current_risk": current_risk,
        "change": change,
        "trend": trend,
    }


# ============================================================
# RISK ACCELERATION
# ============================================================

def calculate_risk_acceleration() -> dict:

    if len(risk_history) < 3:

        return {
            "acceleration_score": 0,
            "acceleration_direction": (
                "INSUFFICIENT_DATA"
            ),
            "risk_velocity": 0,
            "risk_acceleration": 0,
        }

    recent = risk_history[-5:]

    changes = []

    for index in range(
        1,
        len(recent),
    ):

        change = (
            recent[index]
            - recent[index - 1]
        )

        changes.append(change)

    risk_velocity = round(
        sum(changes)
        / len(changes),
        2,
    )

    if len(changes) >= 2:

        recent_change = changes[-1]

        previous_change = changes[-2]

        acceleration = (
            recent_change
            - previous_change
        )

    else:
        acceleration = 0

    acceleration = round(
        acceleration,
        2,
    )

    if acceleration >= 5:

        acceleration_direction = (
            "ACCELERATING"
        )

    elif acceleration <= -5:

        acceleration_direction = (
            "DECELERATING"
        )

    else:

        acceleration_direction = "STABLE"

    if acceleration >= 15:
        acceleration_score = 100

    elif acceleration >= 10:
        acceleration_score = 80

    elif acceleration >= 5:
        acceleration_score = 60

    elif acceleration > 0:
        acceleration_score = 30

    elif acceleration <= -10:
        acceleration_score = 0

    else:
        acceleration_score = 10

    return {
        "acceleration_score": acceleration_score,
        "acceleration_direction": (
            acceleration_direction
        ),
        "risk_velocity": risk_velocity,
        "risk_acceleration": acceleration,
    }


# ============================================================
# TEMPORAL INTELLIGENCE
# ============================================================

def calculate_temporal_intelligence(
    temporal_score: float,
    persistence_percentage: float,
    acceleration_score: float,
    acceleration_direction: str,
) -> dict:

    intelligence_score = (
        temporal_score * 0.50
        + persistence_percentage * 0.30
        + acceleration_score * 0.20
    )

    if acceleration_direction == "ACCELERATING":
        intelligence_score += 10

    elif acceleration_direction == "DECELERATING":
        intelligence_score -= 5

    intelligence_score = min(
        max(
            round(
                intelligence_score,
                2,
            ),
            0,
        ),
        100,
    )

    if intelligence_score >= 75:
        intelligence_state = "SEVERE"

    elif intelligence_score >= 50:
        intelligence_state = "ELEVATED"

    elif intelligence_score >= 25:
        intelligence_state = "WATCH"

    else:
        intelligence_state = "STABLE"

    return {
        "temporal_intelligence_score": (
            intelligence_score
        ),
        "temporal_intelligence_state": (
            intelligence_state
        ),
    }


# ============================================================
# AI DECISION ENGINE
# ============================================================

def calculate_ai_decision(
    risk_score: float,
    temporal_score: float,
    risk_direction: str,
    acceleration_direction: str,
    anomaly_count: int,
    sensor_reliability: float,
) -> dict:

    priority = 0

    priority += risk_score * 0.45

    priority += temporal_score * 0.25

    if risk_direction == "RISING":
        priority += 10

    if acceleration_direction == "ACCELERATING":
        priority += 15

    priority += anomaly_count * 5

    if sensor_reliability >= 90:
        priority += 5

    priority = min(
        round(priority),
        100,
    )

    if priority >= 85:

        level = "URGENT"

        action = (
            "Immediate evacuation and "
            "deploy all rescue teams."
        )

        evacuation = True

    elif priority >= 65:

        level = "HIGH"

        action = (
            "Increase monitoring and "
            "prepare emergency response."
        )

        evacuation = False

    elif priority >= 40:

        level = "MONITOR"

        action = (
            "Continue monitoring and keep "
            "response teams ready."
        )

        evacuation = False

    else:

        level = "NORMAL"

        action = (
            "No immediate intervention "
            "required."
        )

        evacuation = False

    return {
        "response_priority": level,
        "priority_score": priority,
        "response_action": action,
        "evacuation_required": evacuation,
    }


# ============================================================
# RESPONSE PRIORITY
# ============================================================

def calculate_response_priority(
    risk_score: float,
    risk_level: str,
    risk_trend: str,
    anomaly_count: int,
    sensor_reliability: float,
) -> dict:

    priority_score = 0

    # Current risk
    if risk_score >= 80:
        priority_score += 40

    elif risk_score >= 60:
        priority_score += 30

    elif risk_score >= 35:
        priority_score += 20

    else:
        priority_score += 10

    # Trend
    if risk_trend == "RISING":
        priority_score += 25

    elif risk_trend == "STABLE":
        priority_score += 10

    elif risk_trend == "FALLING":
        priority_score += 5

    # Anomaly
    if anomaly_count >= 3:
        priority_score += 20

    elif anomaly_count >= 2:
        priority_score += 15

    elif anomaly_count == 1:
        priority_score += 8

    # Reliability
    if sensor_reliability < 60:
        priority_score += 10

    elif sensor_reliability < 80:
        priority_score += 5

    priority_score = min(
        priority_score,
        100,
    )

    if priority_score >= 75:
        response_priority = "URGENT"

    elif priority_score >= 55:
        response_priority = "HIGH"

    elif priority_score >= 30:
        response_priority = "MONITOR"

    else:
        response_priority = "NORMAL"

    if response_priority == "URGENT":

        response_action = (
            "Prioritize immediate review "
            "of the affected zone and "
            "continuously monitor incoming "
            "sensor data."
        )

    elif response_priority == "HIGH":

        response_action = (
            "Increase monitoring frequency "
            "and prioritize the affected "
            "zone for response planning."
        )

    elif response_priority == "MONITOR":

        response_action = (
            "Continue monitoring sensor "
            "conditions and watch for an "
            "increasing risk trend."
        )

    else:

        response_action = (
            "Continue normal monitoring."
        )

    return {
        "priority_score": priority_score,
        "response_priority": response_priority,
        "response_action": response_action,
    }


# ============================================================
# BASIC FLOOD RISK
# ============================================================

def calculate_flood_risk(
    water_level: float,
    rainfall: float,
    flow_rate: float,
):

    water_score = min(
        (water_level / 3.0) * 40,
        40,
    )

    rainfall_score = min(
        (rainfall / 150) * 35,
        35,
    )

    flow_score = min(
        (flow_rate / 100) * 25,
        25,
    )

    total_score = (
        water_score
        + rainfall_score
        + flow_score
    )

    total_score = round(
        min(total_score, 100),
        1,
    )

    if total_score >= 80:
        risk_level = "CRITICAL"

    elif total_score >= 60:
        risk_level = "HIGH"

    elif total_score >= 35:
        risk_level = "MODERATE"

    else:
        risk_level = "LOW"

    return (
        total_score,
        risk_level,
    )


# ============================================================
# ML PREDICTION HELPER
# ============================================================

def run_ml_prediction(
    sensors: dict,
) -> dict:

    temperature = sensors.get(
        "temperature",
        28,
    )

    humidity = sensors.get(
        "humidity",
        80,
    )

    wind_speed = sensors.get(
        "wind_speed",
        15,
    )

    features = [
        [
            sensors["rainfall"],
            sensors["water_level"],
            sensors["flow_rate"],
            temperature,
            humidity,
            wind_speed,
        ]
    ]

    prediction = model.predict(
        features
    )[0]

    probabilities = model.predict_proba(
        features
    )[0]

    # Safely locate class 1
    flood_probability = 0.0

    if hasattr(model, "classes_"):

        classes = list(
            model.classes_
        )

        if 1 in classes:

            class_index = classes.index(1)

            flood_probability = (
                probabilities[class_index]
                * 100
            )

        elif len(probabilities) > 1:

            flood_probability = (
                probabilities[1]
                * 100
            )

    elif len(probabilities) > 1:

        flood_probability = (
            probabilities[1]
            * 100
        )

    flood_probability = round(
        flood_probability,
        2,
    )

    if flood_probability >= 80:
        risk_level = "CRITICAL"

    elif flood_probability >= 60:
        risk_level = "HIGH"

    elif flood_probability >= 35:
        risk_level = "MODERATE"

    else:
        risk_level = "LOW"

    return {
        "prediction": int(prediction),
        "flood_probability": (
            flood_probability
        ),
        "risk_level": risk_level,
        "inputs": {
            "rainfall": sensors["rainfall"],
            "water_level": sensors["water_level"],
            "flow_rate": sensors["flow_rate"],
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind_speed,
        },
    }


# ============================================================
# INTELLIGENT PREDICTION CORE
# ============================================================

def calculate_intelligent_prediction(
    sensors: Optional[dict] = None,
    *,
    update_history: bool = False,
) -> dict:

    if sensors is None:

        sensors = (
            get_latest_sensor_data()
            .copy()
        )

    # --------------------------------------------------------
    # Reliability
    # --------------------------------------------------------

    reliability_result = (
        calculate_sensor_reliability(
            sensors["water_level"],
            sensors["rainfall"],
            sensors["flow_rate"],
        )
    )

    # --------------------------------------------------------
    # Anomalies
    # --------------------------------------------------------

    anomaly_result = (
        detect_sensor_anomalies(
            sensors
        )
    )

    # --------------------------------------------------------
    # Fusion
    # --------------------------------------------------------

    fusion_result = (
        calculate_sensor_fusion(
            sensors,
            reliability_result[
                "sensor_reliability"
            ],
        )
    )

    # --------------------------------------------------------
    # ML
    # --------------------------------------------------------

    ml_result = run_ml_prediction(
        sensors
    )

    prediction = ml_result[
        "prediction"
    ]

    flood_probability = ml_result[
        "flood_probability"
    ]

    # --------------------------------------------------------
    # Temporal
    # --------------------------------------------------------

    temporal_result = (
        calculate_temporal_risk()
    )

    # --------------------------------------------------------
    # Acceleration
    # --------------------------------------------------------

    acceleration_result = (
        calculate_risk_acceleration()
    )

    # --------------------------------------------------------
    # Temporal intelligence
    # --------------------------------------------------------

    temporal_intelligence_result = (
        calculate_temporal_intelligence(
            temporal_score=temporal_result[
                "temporal_score"
            ],
            persistence_percentage=(
                temporal_result[
                    "persistence_percentage"
                ]
            ),
            acceleration_score=(
                acceleration_result[
                    "acceleration_score"
                ]
            ),
            acceleration_direction=(
                acceleration_result[
                    "acceleration_direction"
                ]
            ),
        )
    )

    # --------------------------------------------------------
    # Environmental score
    # --------------------------------------------------------

    environmental_score = (
        fusion_result[
            "fused_environmental_score"
        ]
    )

    overall_reliability = (
        reliability_result[
            "overall_reliability"
        ]
    )

    # --------------------------------------------------------
    # Anomaly count
    # --------------------------------------------------------

    anomaly_count = sum(
        1
        for value in anomaly_result.values()
        if value["anomaly"]
    )

    # --------------------------------------------------------
    # Temporal intelligence score
    # --------------------------------------------------------

    temporal_intelligence_score = (
        temporal_intelligence_result[
            "temporal_intelligence_score"
        ]
    )

    # --------------------------------------------------------
    # Adaptive risk fusion
    # --------------------------------------------------------

    risk_score = (
        flood_probability * 0.55
        + environmental_score * 0.20
        + overall_reliability * 0.10
        + temporal_intelligence_score * 0.15
    )

    if anomaly_count >= 2:
        risk_score += 10

    risk_score = min(
        round(risk_score, 2),
        100,
    )

    # --------------------------------------------------------
    # Risk level
    # --------------------------------------------------------

    if risk_score >= 80:
        risk_level = "CRITICAL"

    elif risk_score >= 60:
        risk_level = "HIGH"

    elif risk_score >= 35:
        risk_level = "MODERATE"

    else:
        risk_level = "LOW"

    # --------------------------------------------------------
    # Risk trend
    # --------------------------------------------------------

    trend_result = calculate_risk_trend(
        risk_score,
        append=update_history,
    )

    # --------------------------------------------------------
    # AI decision
    # --------------------------------------------------------

    decision_result = calculate_ai_decision(
        risk_score=risk_score,
        temporal_score=temporal_result[
            "temporal_score"
        ],
        risk_direction=temporal_result[
            "risk_direction"
        ],
        acceleration_direction=(
            acceleration_result[
                "acceleration_direction"
            ]
        ),
        anomaly_count=anomaly_count,
        sensor_reliability=overall_reliability,
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    result = {
        "prediction": int(prediction),

        "flood_probability": (
            flood_probability
        ),

        "environmental_score": (
            environmental_score
        ),

        "sensor_reliability": (
            overall_reliability
        ),

        "anomaly_count": anomaly_count,

        "adaptive_risk_score": (
            risk_score
        ),

        "risk_level": risk_level,

        "sensor_weights": (
            fusion_result[
                "sensor_weights"
            ]
        ),

        "sensor_data": sensors,

        "temporal_score": (
            temporal_result[
                "temporal_score"
            ]
        ),

        "risk_direction": (
            temporal_result[
                "risk_direction"
            ]
        ),

        "temporal_persistence": (
            temporal_result[
                "persistence"
            ]
        ),

        "temporal_persistence_percentage": (
            temporal_result[
                "persistence_percentage"
            ]
        ),

        "acceleration_score": (
            acceleration_result[
                "acceleration_score"
            ]
        ),

        "acceleration_direction": (
            acceleration_result[
                "acceleration_direction"
            ]
        ),

        "risk_velocity": (
            acceleration_result[
                "risk_velocity"
            ]
        ),

        "risk_acceleration": (
            acceleration_result[
                "risk_acceleration"
            ]
        ),

        "temporal_intelligence_score": (
            temporal_intelligence_score
        ),

        "temporal_intelligence_state": (
            temporal_intelligence_result[
                "temporal_intelligence_state"
            ]
        ),

        "response_priority": (
            decision_result[
                "response_priority"
            ]
        ),

        "priority_score": (
            decision_result[
                "priority_score"
            ]
        ),

        "recommended_action": (
            decision_result[
                "response_action"
            ]
        ),

        "evacuation_required": (
            decision_result[
                "evacuation_required"
            ]
        ),

        "trend": trend_result,
    }

    return result


# ============================================================
# CENTRAL AI UPDATE PIPELINE
# ============================================================

def update_ai_state(
    sensor_input: Optional[dict] = None,
    *,
    source: str = "controlled_simulation",
) -> dict:

    global latest_sensor_data
    global latest_ai_snapshot

    with state_lock:

        # ----------------------------------------------------
        # Generate / receive sensor data
        # ----------------------------------------------------

        if sensor_input is None:

            sensor_input = (
                generate_controlled_sensor_data()
            )

        simulation_phase = (
            sensor_input.get(
                "simulation_phase"
            )
        )

        simulation_number = (
            sensor_input.get(
                "simulation_step"
            )
        )

        clean_sensor_input = {
            "water_level": sensor_input[
                "water_level"
            ],
            "rainfall": sensor_input[
                "rainfall"
            ],
            "flow_rate": sensor_input[
                "flow_rate"
            ],
            "temperature": sensor_input.get(
                "temperature",
                28.0,
            ),
            "humidity": sensor_input.get(
                "humidity",
                80.0,
            ),
            "wind_speed": sensor_input.get(
                "wind_speed",
                15.0,
            ),
        }

        # ----------------------------------------------------
        # Update sensor service
        # ----------------------------------------------------

        sensor_data = update_sensor_data(
            clean_sensor_input,
            source=source,
        )

        if simulation_phase is not None:
            sensor_data[
                "simulation_phase"
            ] = simulation_phase

        if simulation_number is not None:
            sensor_data[
                "simulation_step"
            ] = simulation_number

        latest_sensor_data = (
            sensor_data.copy()
        )

        # ----------------------------------------------------
        # Store sensor history
        # ----------------------------------------------------

        history = get_sensor_history()

        history.append(
            latest_sensor_data.copy()
        )

        if len(history) > MAX_SENSOR_HISTORY:
            history.pop(0)

        # ----------------------------------------------------
        # Complete AI analysis
        # ----------------------------------------------------

        prediction_data = (
            calculate_intelligent_prediction(
                latest_sensor_data,
                update_history=True,
            )
        )

        trend_result = prediction_data.pop(
            "trend"
        )

        current_risk = prediction_data[
            "adaptive_risk_score"
        ]

        # ----------------------------------------------------
        # Response priority
        # ----------------------------------------------------

        priority_result = (
            calculate_response_priority(
                risk_score=current_risk,
                risk_level=prediction_data[
                    "risk_level"
                ],
                risk_trend=trend_result[
                    "trend"
                ],
                anomaly_count=prediction_data[
                    "anomaly_count"
                ],
                sensor_reliability=(
                    prediction_data[
                        "sensor_reliability"
                    ]
                ),
            )
        )

        prediction_data[
            "recommended_action"
        ] = priority_result[
            "response_action"
        ]

        prediction_data[
            "response_priority"
        ] = priority_result[
            "response_priority"
        ]

        prediction_data[
            "priority_score"
        ] = priority_result[
            "priority_score"
        ]

        # ----------------------------------------------------
        # Store snapshot
        # ----------------------------------------------------

        latest_ai_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "risk": prediction_data,
            "trend": trend_result,
        }

        # ----------------------------------------------------
        # Risk history log
        # ----------------------------------------------------

        risk_history_log.append(
            {
                "timestamp": datetime.now().strftime(
                    "%H:%M:%S"
                ),

                "risk_score": prediction_data[
                    "adaptive_risk_score"
                ],

                "risk_level": prediction_data[
                    "risk_level"
                ],

                "trend": trend_result[
                    "trend"
                ],

                "risk_change": trend_result[
                    "change"
                ],

                "water_level": latest_sensor_data[
                    "water_level"
                ],

                "rainfall": latest_sensor_data[
                    "rainfall"
                ],

                "flow_rate": latest_sensor_data[
                    "flow_rate"
                ],

                "response_priority": prediction_data[
                    "response_priority"
                ],

                "recommended_action": prediction_data[
                    "recommended_action"
                ],
            }
        )

        if len(risk_history_log) > MAX_RISK_LOG:
            risk_history_log.pop(0)

        logger.info(
            "AI update | step=%s | phase=%s | risk=%.2f | level=%s",
            latest_sensor_data.get(
                "simulation_step"
            ),
            latest_sensor_data.get(
                "simulation_phase"
            ),
            prediction_data[
                "adaptive_risk_score"
            ],
            prediction_data[
                "risk_level"
            ],
        )

        return latest_ai_snapshot


# ============================================================
# BACKGROUND 5-SECOND AI ENGINE
# ============================================================

async def background_ai_loop():
    """
    Continuously updates sensor and AI state every 5 seconds.
    """

    logger.info(
        "5-second DisasterAI background engine started."
    )

    # Initial update immediately after startup
    try:

        await asyncio.to_thread(
            update_ai_state,
            None,
            source="controlled_simulation",
        )

    except Exception:
        logger.exception(
            "Initial AI update failed."
        )

    while True:

        try:

            await asyncio.sleep(
                SIMULATION_INTERVAL_SECONDS
            )

            await asyncio.to_thread(
                update_ai_state,
                None,
                source="controlled_simulation",
            )

        except asyncio.CancelledError:

            logger.info(
                "5-second AI background engine stopped."
            )

            raise

        except Exception:

            logger.exception(
                "Background AI update failed."
            )


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    global background_task

    background_task = asyncio.create_task(
        background_ai_loop()
    )

    logger.info(
        "DisasterAI API started."
    )

    yield

    if background_task is not None:

        background_task.cancel()

        try:
            await background_task

        except asyncio.CancelledError:
            pass

    logger.info(
        "DisasterAI API shutdown complete."
    )


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="DisasterAI API",
    description=(
        "AI-powered disaster management "
        "backend with real-time sensor "
        "simulation and adaptive risk analysis."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def home():

    return {
        "system": "DisasterAI",
        "status": "online",
        "message": (
            "Disaster management backend "
            "is running"
        ),
        "auto_update_interval": (
            f"{SIMULATION_INTERVAL_SECONDS} seconds"
        ),
    }


# ============================================================
# SYSTEM STATUS
# ============================================================

@app.get("/api/status")
def system_status():

    with state_lock:

        current_risk = None
        current_level = None

        if latest_ai_snapshot:

            current_risk = (
                latest_ai_snapshot[
                    "risk"
                ][
                    "adaptive_risk_score"
                ]
            )

            current_level = (
                latest_ai_snapshot[
                    "risk"
                ][
                    "risk_level"
                ]
            )

        return {
            "status": "online",
            "ai_engine": "adaptive_intelligence",
            "sensors": "online",
            "simulation": "controlled",
            "auto_update": True,
            "update_interval_seconds": (
                SIMULATION_INTERVAL_SECONDS
            ),
            "simulation_step": simulation_step,
            "current_risk": current_risk,
            "current_risk_level": current_level,
            "alerts": 3,
        }


# ============================================================
# IMD TEST
# ============================================================

@app.get("/api/imd/test")
def imd_test():

    result = get_imd_data(
        "/api/v1/current_wx"
    )

    return result


# ============================================================
# MANUAL SENSOR INPUT
# ============================================================

@app.post("/api/sensors/input")
def receive_sensor_data(
    data: SensorData,
):

    sensor_input = {
        "water_level": data.water_level,
        "rainfall": data.rainfall,
        "flow_rate": data.flow_rate,
        "temperature": 28.0,
        "humidity": 80.0,
        "wind_speed": 15.0,
    }

    snapshot = update_ai_state(
        sensor_input,
        source="manual_input",
    )

    return {
        "status": "received",
        "sensor_data": (
            latest_sensor_data.copy()
        ),
        "ai": snapshot,
        "history_length": len(
            get_sensor_history()
        ),
    }


# ============================================================
# SENSOR DATA
# ============================================================

@app.get("/api/sensors")
def get_sensor_data():

    """
    Returns the latest sensor snapshot.

    IMPORTANT:
    This endpoint no longer advances the simulation.

    The background AI engine advances it every
    5 seconds. This prevents multiple frontend
    requests from accidentally accelerating
    the simulation.
    """

    with state_lock:

        return latest_sensor_data.copy()


# ============================================================
# IMD WEATHER
# ============================================================

@app.get("/api/imd")
def imd_weather():

    imd_result = get_imd_data()

    result = update_from_imd(
        imd_result
    )

    return result


# ============================================================
# ALERTS
# ============================================================

@app.get("/api/alerts")
def alerts():

    return {
        "total": 3,

        "alerts": [
            {
                "id": 1,
                "level": "critical",
                "title": "Flood Risk Increased",
                "location": "Sector 4",
                "time": "2 min ago",
            },

            {
                "id": 2,
                "level": "high",
                "title": "Road Blocked",
                "location": "Bridge Road",
                "time": "8 min ago",
            },

            {
                "id": 3,
                "level": "high",
                "title": "Water Level Rising",
                "location": "River Station 02",
                "time": "12 min ago",
            },
        ],
    }


# ============================================================
# AI RECOMMENDATIONS
# ============================================================

@app.get("/api/ai/recommendations")
def ai_recommendations():

    return {
        "engine": (
            "DisasterAI Decision Support"
        ),

        "mode": (
            "controlled_simulation"
        ),

        "recommendations": [
            "Evacuate vulnerable residents from Zone A.",
            "Deploy Rescue Team 2 to Sector 4.",
            "Bridge Road may become inaccessible within 30 minutes.",
            "Move Ambulance 04 closer to Government School shelter.",
        ],
    }


# ============================================================
# BASIC FLOOD RISK API
# ============================================================

@app.get("/api/ai/risk")
def ai_risk():

    with state_lock:

        sensors = latest_sensor_data.copy()

    score, risk_level = calculate_flood_risk(
        sensors["water_level"],
        sensors["rainfall"],
        sensors["flow_rate"],
    )

    if risk_level == "CRITICAL":

        action = (
            "Initiate emergency evacuation "
            "and deploy all available "
            "rescue teams."
        )

    elif risk_level == "HIGH":

        action = (
            "Prepare evacuation of vulnerable "
            "areas and deploy additional "
            "rescue teams."
        )

    elif risk_level == "MODERATE":

        action = (
            "Increase monitoring and prepare "
            "emergency response teams."
        )

    else:

        action = (
            "Continue normal monitoring and "
            "maintain emergency readiness."
        )

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "inputs": {
            "water_level": sensors[
                "water_level"
            ],
            "rainfall": sensors[
                "rainfall"
            ],
            "flow_rate": sensors[
                "flow_rate"
            ],
        },
        "recommended_action": action,
    }


# ============================================================
# ML PREDICTION API
# ============================================================

@app.get("/api/ai/ml-prediction")
def ml_prediction():

    with state_lock:

        sensors = latest_sensor_data.copy()

    return run_ml_prediction(
        sensors
    )


# ============================================================
# SENSOR RELIABILITY API
# ============================================================

@app.get("/api/ai/sensor-reliability")
def sensor_reliability():

    with state_lock:

        sensors = latest_sensor_data.copy()

    result = calculate_sensor_reliability(
        sensors["water_level"],
        sensors["rainfall"],
        sensors["flow_rate"],
    )

    return {
        "inputs": sensors,
        **result,
    }


# ============================================================
# ANOMALY API
# ============================================================

@app.get("/api/ai/anomalies")
def sensor_anomalies():

    with state_lock:

        current_data = (
            latest_sensor_data.copy()
        )

    anomalies = detect_sensor_anomalies(
        current_data
    )

    return {
        "current_data": current_data,
        "anomalies": anomalies,
        "history_length": len(
            get_sensor_history()
        ),
    }


# ============================================================
# SENSOR FUSION API
# ============================================================

@app.get("/api/ai/sensor-fusion")
def sensor_fusion():

    with state_lock:

        sensors = latest_sensor_data.copy()

    reliability_result = (
        calculate_sensor_reliability(
            sensors["water_level"],
            sensors["rainfall"],
            sensors["flow_rate"],
        )
    )

    fusion_result = (
        calculate_sensor_fusion(
            sensors,
            reliability_result[
                "sensor_reliability"
            ],
        )
    )

    return {
        "sensor_data": sensors,
        "reliability": reliability_result,
        "fusion": fusion_result,
    }


# ============================================================
# TEMPORAL RISK API
# ============================================================

@app.get("/api/ai/temporal-risk")
def temporal_risk():

    return calculate_temporal_risk()


# ============================================================
# INTELLIGENT PREDICTION API
# ============================================================

@app.get("/api/ai/intelligent-prediction")
def intelligent_prediction():

    with state_lock:

        if latest_ai_snapshot is None:

            update_ai_state(
                source="controlled_simulation"
            )

        return latest_ai_snapshot[
            "risk"
        ].copy()


# ============================================================
# RISK TREND API
# ============================================================

@app.get("/api/ai/risk-trend")
def risk_trend():

    with state_lock:

        if latest_ai_snapshot is None:

            update_ai_state(
                source="controlled_simulation"
            )

        return latest_ai_snapshot.copy()


# ============================================================
# RISK HISTORY API
# ============================================================

@app.get("/api/ai/risk-history")
def risk_history_data():

    with state_lock:

        return {
            "count": len(
                risk_history_log
            ),

            "history": (
                list(risk_history_log)
            ),
        }


# ============================================================
# RISK ACCELERATION API
# ============================================================

@app.get("/api/ai/risk-acceleration")
def risk_acceleration():

    with state_lock:

        return calculate_risk_acceleration()


# ============================================================
# RESPONSE PRIORITY API
# ============================================================

@app.get("/api/ai/response-priority")
def response_priority():

    with state_lock:

        if latest_ai_snapshot is None:

            update_ai_state(
                source="controlled_simulation"
            )

        risk = latest_ai_snapshot[
            "risk"
        ]

        trend = latest_ai_snapshot[
            "trend"
        ]

        return {
            "risk": risk,
            "trend": trend,
            "response": {
                "priority_score": risk[
                    "priority_score"
                ],

                "response_priority": risk[
                    "response_priority"
                ],

                "response_action": risk[
                    "recommended_action"
                ],
            },
        }


# ============================================================
# SENSOR SERVICE TEST
# ============================================================

@app.get("/api/sensors/service-test")
def sensor_service_test():

    with state_lock:

        return {
            "latest_sensor_data": (
                get_latest_sensor_data()
            ),

            "history_length": len(
                get_sensor_history()
            ),
        }


# ============================================================
# DASHBOARD API
# ============================================================

@app.get("/api/dashboard")
def get_dashboard():

    with state_lock:

        if latest_ai_snapshot is None:

            update_ai_state(
                source="controlled_simulation"
            )

        return {
            "sensors": (
                latest_sensor_data.copy()
            ),

            "risk": (
                latest_ai_snapshot.copy()
                if latest_ai_snapshot
                else None
            ),

            "alerts": alerts(),

            "recommendations": (
                ai_recommendations()
            ),

            "system": {
                "status": "online",
                "auto_update": True,
                "update_interval_seconds": (
                    SIMULATION_INTERVAL_SECONDS
                ),
                "simulation_step": (
                    simulation_step
                ),
            },
        }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    with state_lock:

        return {
            "status": "healthy",
            "service": "DisasterAI",
            "model_loaded": model is not None,
            "background_engine": (
                background_task is not None
                and not background_task.done()
            ),
            "update_interval_seconds": (
                SIMULATION_INTERVAL_SECONDS
            ),
            "simulation_step": simulation_step,
        }