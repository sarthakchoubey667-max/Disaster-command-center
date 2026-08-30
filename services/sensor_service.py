from typing import Dict, List
from datetime import datetime


# -----------------------------------------
# LATEST SENSOR DATA
# -----------------------------------------

latest_sensor_data = {
    "water_level": 2.4,
    "rainfall": 110,
    "flow_rate": 78,
    "temperature": 28,
    "humidity": 80,
    "wind_speed": 15,
    "source": "simulation",
    "timestamp": None
}


# -----------------------------------------
# SENSOR HISTORY
# -----------------------------------------

sensor_history: List[Dict] = []


# -----------------------------------------
# UPDATE SENSOR DATA
# -----------------------------------------

def update_sensor_data(data: Dict, source: str = "simulation") -> Dict:

    global latest_sensor_data

    latest_sensor_data = {
        "water_level": data.get(
            "water_level",
            latest_sensor_data["water_level"]
        ),

        "rainfall": data.get(
            "rainfall",
            latest_sensor_data["rainfall"]
        ),

        "flow_rate": data.get(
            "flow_rate",
            latest_sensor_data["flow_rate"]
        ),

        "temperature": data.get(
            "temperature",
            latest_sensor_data["temperature"]
        ),

        "humidity": data.get(
            "humidity",
            latest_sensor_data["humidity"]
        ),

        "wind_speed": data.get(
            "wind_speed",
            latest_sensor_data["wind_speed"]
        ),

        "source": source,

        "timestamp": datetime.now().isoformat()
    }

    sensor_history.append(
        latest_sensor_data.copy()
    )

    # Keep only the latest 50 readings
    if len(sensor_history) > 50:
        sensor_history.pop(0)

    return latest_sensor_data


# -----------------------------------------
# GET LATEST SENSOR DATA
# -----------------------------------------

def get_latest_sensor_data() -> Dict:

    return latest_sensor_data


# -----------------------------------------
# GET SENSOR HISTORY
# -----------------------------------------

def get_sensor_history() -> List[Dict]:

    return sensor_history
# -----------------------------------------
# UPDATE SENSOR DATA FROM IMD
# -----------------------------------------

def update_from_imd(imd_result: Dict) -> Dict:
    """
    Merge IMD weather data with the existing
    water-level and flow-rate sensor data.
    """

    if not imd_result.get("success"):
        return {
            "success": False,
            "error": imd_result.get("error", "IMD data unavailable"),
            "data": get_latest_sensor_data()
        }

    imd_data = imd_result.get("data", {})

    # Keep existing physical/simulated sensor values
    current = get_latest_sensor_data()

    combined_data = {
        "water_level": current.get("water_level", 2.4),
        "flow_rate": current.get("flow_rate", 78),

        # Weather data from IMD
        "rainfall": imd_data.get(
            "rainfall",
            current.get("rainfall", 110)
        ),

        "temperature": imd_data.get(
            "temperature",
            current.get("temperature", 28)
        ),

        "humidity": imd_data.get(
            "humidity",
            current.get("humidity", 80)
        ),

        "wind_speed": imd_data.get(
            "wind_speed",
            current.get("wind_speed", 15)
        )
    }

    # Update central sensor store
    updated = update_sensor_data(
        combined_data,
        source=imd_result.get("source", "IMD")
    )

    return {
        "success": True,
        "data": updated
    }