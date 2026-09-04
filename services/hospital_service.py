import json
import os
import sqlite3
from datetime import datetime, timezone


DATA_DIR = os.getenv("DISASTER_DATA_DIR", "./data")
DB_PATH = os.path.join(DATA_DIR, "disaster_command.db")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_hospital_store():
    with _connect() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS hospital_status (
                user_id INTEGER PRIMARY KEY,
                beds_total INTEGER NOT NULL DEFAULT 50,
                beds_available INTEGER NOT NULL DEFAULT 42,
                icu_total INTEGER NOT NULL DEFAULT 10,
                icu_available INTEGER NOT NULL DEFAULT 8,
                emergency_beds INTEGER NOT NULL DEFAULT 6,
                ambulances_available INTEGER NOT NULL DEFAULT 3,
                oxygen_units INTEGER NOT NULL DEFAULT 24,
                blood_bank_available INTEGER NOT NULL DEFAULT 1,
                incoming_cases INTEGER NOT NULL DEFAULT 0,
                casualties_admitted INTEGER NOT NULL DEFAULT 0,
                shortage_note TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rescue_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                vehicle_number TEXT,
                vehicle_type TEXT,
                team_members TEXT NOT NULL DEFAULT '[]',
                equipment_status TEXT,
                blockage_status TEXT,
                critical_count INTEGER NOT NULL DEFAULT 0,
                serious_count INTEGER NOT NULL DEFAULT 0,
                minor_count INTEGER NOT NULL DEFAULT 0,
                destination_hospital TEXT,
                latitude REAL,
                longitude REAL,
                created_at TEXT NOT NULL
            );
        """)


def get_hospital_status(user_id: int):
    with _connect() as connection:
        row = connection.execute("SELECT * FROM hospital_status WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            connection.execute("INSERT INTO hospital_status(user_id,updated_at) VALUES(?,?)", (user_id, _now()))
            row = connection.execute("SELECT * FROM hospital_status WHERE user_id=?", (user_id,)).fetchone()
        return dict(row)


def update_hospital_status(user_id: int, payload: dict):
    allowed = {"beds_total", "beds_available", "icu_total", "icu_available", "emergency_beds", "ambulances_available", "oxygen_units", "blood_bank_available", "incoming_cases", "casualties_admitted", "shortage_note"}
    current = get_hospital_status(user_id)
    values = {key: payload.get(key, current[key]) for key in allowed}
    values["updated_at"] = _now()
    assignments = ",".join(f"{key}=?" for key in values)
    with _connect() as connection:
        connection.execute(f"UPDATE hospital_status SET {assignments} WHERE user_id=?", (*values.values(), user_id))
    return get_hospital_status(user_id)


def add_rescue_update(user_id: int, payload: dict):
    fields = ("vehicle_number", "vehicle_type", "equipment_status", "blockage_status", "critical_count", "serious_count", "minor_count", "destination_hospital", "latitude", "longitude")
    defaults = {"vehicle_number": "", "vehicle_type": "BLS", "equipment_status": "Ready", "blockage_status": "Clear", "critical_count": 0, "serious_count": 0, "minor_count": 0, "destination_hospital": "Nearest safe hospital", "latitude": None, "longitude": None}
    values = [payload.get(field, defaults[field]) for field in fields]
    with _connect() as connection:
        cursor = connection.execute("""INSERT INTO rescue_updates(user_id,vehicle_number,vehicle_type,team_members,equipment_status,blockage_status,critical_count,serious_count,minor_count,destination_hospital,latitude,longitude,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (user_id, values[0], values[1], json.dumps(payload.get("team_members") or []), *values[2:], _now()))
        return {"status": "success", "update_id": cursor.lastrowid}


def list_rescue_updates(limit: int = 25):
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM rescue_updates ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 100)),)).fetchall()
    output = []
    for row in rows:
        item = dict(row)
        item["team_members"] = json.loads(item["team_members"] or "[]")
        output.append(item)
    return output
