import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(os.getenv("DISASTER_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "disaster_reports.db"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_REPORT_TYPES = {"crack", "slope_movement", "blocked_road", "landslide", "flooding", "other"}
ALLOWED_SEVERITIES = {"low", "moderate", "high", "critical"}
ALLOWED_MEDIA_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "video/mp4": ".mp4", "video/webm": ".webm"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_REPORT_UPLOAD_MB", "10")) * 1024 * 1024


def _connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_report_store():
    with _connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS field_reports (
                id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                reporter_name TEXT,
                road_status TEXT NOT NULL DEFAULT 'unknown',
                media_url TEXT,
                media_type TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)


def save_media(content: bytes, content_type: str | None) -> tuple[str, str]:
    extension = ALLOWED_MEDIA_TYPES.get(content_type or "")
    if not extension:
        raise ValueError("Only JPG, PNG, WEBP, MP4 and WEBM media are allowed")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Media must be smaller than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    filename = f"{uuid.uuid4().hex}{extension}"
    (UPLOAD_DIR / filename).write_bytes(content)
    return f"/uploads/{filename}", content_type or "application/octet-stream"


def create_report(*, report_type, severity, description, latitude, longitude, reporter_name=None, road_status="unknown", media_url=None, media_type=None):
    if report_type not in ALLOWED_REPORT_TYPES:
        raise ValueError("Unsupported report type")
    if severity not in ALLOWED_SEVERITIES:
        raise ValueError("Unsupported severity")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Invalid coordinates")
    report = {
        "id": str(uuid.uuid4()), "report_type": report_type, "severity": severity,
        "description": description.strip(), "latitude": latitude, "longitude": longitude,
        "reporter_name": (reporter_name or "Field reporter").strip(), "road_status": road_status,
        "media_url": media_url, "media_type": media_type, "status": "new",
        "created_at": datetime.now(timezone.utc).isoformat(), "metadata": {},
    }
    with _connection() as connection:
        connection.execute(
            """INSERT INTO field_reports (id, report_type, severity, description, latitude, longitude, reporter_name, road_status, media_url, media_type, status, created_at, metadata)
               VALUES (:id, :report_type, :severity, :description, :latitude, :longitude, :reporter_name, :road_status, :media_url, :media_type, :status, :created_at, :metadata)""",
            {**report, "metadata": json.dumps(report["metadata"])},
        )
    return report


def list_reports(limit=100):
    initialize_report_store()
    with _connection() as connection:
        rows = connection.execute("SELECT * FROM field_reports ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
    reports = []
    for row in rows:
        report = dict(row)
        report["metadata"] = json.loads(report.get("metadata") or "{}")
        reports.append(report)
    return reports
