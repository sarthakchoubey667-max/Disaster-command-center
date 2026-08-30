from services.sensor_service import (
    update_sensor_data,
    get_latest_sensor_data,
    get_sensor_history
)


# Test simulated sensor
data = update_sensor_data(
    {
        "water_level": 3.2,
        "rainfall": 185,
        "flow_rate": 120
    },
    source="simulation"
)

print("LATEST DATA:")
print(data)

print("\nHISTORY:")
print(get_sensor_history())