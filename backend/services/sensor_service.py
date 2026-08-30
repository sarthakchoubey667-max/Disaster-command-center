from datetime import datetime
from typing import Dict

# Latest sensor reading
latest_sensor_data = {
    "water_level": 3.2,
    "rainfall": 185,
    "flow_rate": 120,
    "temperature": 28,
    "humidity": 80,
    "wind_speed": 15,
    "source": "simulation",
    "timestamp": datetime.now().isoformat()
}

# Sensor history
sensor_history = []


def update_sensor_data(data,source="simulation") -> Dict:
    """
    Update the latest sensor data and store it in history.
    """

    global latest_sensor_data

    latest_sensor_data = {
        **data,
        "source": source,
        "timestamp": datetime.now().isoformat()
    }

    sensor_history.append(latest_sensor_data.copy())

    # Keep latest 20 readings
    if len(sensor_history) > 20:
        sensor_history.pop(0)

    return latest_sensor_data


def get_latest_sensor_data():
    """
    Return the latest sensor reading.
    """
    return latest_sensor_data.copy()


def get_sensor_history():
    """
    Return sensor history.
    """
    return sensor_history.copy()
# -----------------------------------------
# UPDATE SENSOR DATA FROM IMD
# -----------------------------------------

def update_from_imd(imd_result: Dict) -> Dict:
    """
    Merge IMD weather data with existing
    water-level and flow-rate sensor data.
    """

    if not imd_result.get("success"):
        return {
            "success": False,
            "error": imd_result.get(
                "error",
                "IMD data unavailable"
            ),
            "data": get_latest_sensor_data()
        }

    imd_data = imd_result.get("data", {})

    # Get existing sensor values
    current = get_latest_sensor_data()

    # Combine sensor + IMD data
    combined_data = {
        "water_level": current.get("water_level", 2.4),
        "flow_rate": current.get("flow_rate", 78),

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

    # Store combined data
    combined_data["source"] = imd_result.get("source", "IMD")

    updated = update_sensor_data(combined_data, source=imd_result.get("source", "IMD"))

    return {
    "success": True,
    "data": updated
    }