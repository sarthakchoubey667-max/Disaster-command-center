import random
import csv

random.seed(42)

rows = []

for _ in range(2000):

    rainfall = round(random.uniform(0, 200), 1)
    water_level = round(random.uniform(0.5, 3.5), 2)
    flow_rate = round(random.uniform(20, 120), 1)
    temperature = round(random.uniform(15, 40), 1)
    humidity = round(random.uniform(30, 100), 1)
    wind_speed = round(random.uniform(0, 50), 1)

    # Calculate a synthetic flood-risk score
    risk_score = (
        (rainfall / 200) * 40 +
        (water_level / 3.5) * 35 +
        (flow_rate / 120) * 25
    )

    # Add a small amount of randomness
    risk_score += random.uniform(-5, 5)

    flood = 1 if risk_score >= 60 else 0

    rows.append([
        rainfall,
        water_level,
        flow_rate,
        temperature,
        humidity,
        wind_speed,
        flood
    ])

with open("flood_data.csv", "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "rainfall",
        "water_level",
        "flow_rate",
        "temperature",
        "humidity",
        "wind_speed",
        "flood"
    ])

    writer.writerows(rows)

print("Dataset generated successfully!")
print("Total records:", len(rows))