import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import requests

from services.external_base import DEFAULT_TIMEOUT


DATA_DIR = os.getenv("DISASTER_DATA_DIR", "./data")
DB_PATH = os.path.join(DATA_DIR, "disaster_command.db")
PUBLIC_ROLES = {"citizen", "police", "fire", "rescue"}


def _now():
    return datetime.now(timezone.utc)


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _password_hash(password: str, salt: bytes | None = None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}:{digest.hex()}"


def _password_valid(password: str, stored: str):
    try:
        salt_hex, expected = stored.split(":", 1)
        actual = _password_hash(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _token_hash(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def initialize_auth_store():
    with _connect() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                mobile TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                location TEXT,
                official_details TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL,
                email_verified INTEGER NOT NULL DEFAULT 0,
                verification_hash TEXT,
                verification_expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """)
    _bootstrap_operator()


def _bootstrap_operator():
    email = os.getenv("OPERATOR_EMAIL", "").strip().lower()
    password = os.getenv("OPERATOR_PASSWORD", "")
    if not email or len(password) < 10:
        return
    now = _now().isoformat()
    with _connect() as connection:
        existing = connection.execute("SELECT id FROM users WHERE role = 'operator'").fetchone()
        if existing:
            connection.execute("UPDATE users SET email=?, password_hash=?, status='active', email_verified=1, updated_at=? WHERE id=?", (email, _password_hash(password), now, existing["id"]))
        else:
            connection.execute("INSERT INTO users(full_name,email,password_hash,role,status,email_verified,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (os.getenv("OPERATOR_NAME", "System Operator"), email, _password_hash(password), "operator", "active", 1, now, now))


def _public_user(row):
    details = json.loads(row["official_details"] or "{}")
    return {"id": row["id"], "full_name": row["full_name"], "email": row["email"], "mobile": row["mobile"], "role": row["role"], "location": row["location"], "official_details": details, "status": row["status"], "email_verified": bool(row["email_verified"]), "created_at": row["created_at"]}


def register_user(payload: dict):
    role = str(payload.get("role", "")).lower()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if role not in PUBLIC_ROLES:
        raise ValueError("Select a valid account type")
    if "@" not in email:
        raise ValueError("Enter a valid email address")
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = _now()
    status = "email_verification"
    try:
        with _connect() as connection:
            cursor = connection.execute("""INSERT INTO users(full_name,email,mobile,password_hash,role,location,official_details,status,email_verified,verification_hash,verification_expires_at,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (str(payload.get("full_name", "")).strip(), email, str(payload.get("mobile", "")).strip(), _password_hash(password), role, str(payload.get("location", "")).strip(), json.dumps(payload.get("official_details") or {}), status, 0, _token_hash(code), (now + timedelta(minutes=15)).isoformat(), now.isoformat(), now.isoformat()))
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
        raise ValueError("An account with this email already exists") from error
    try:
        delivered = _send_verification_email(email, str(payload.get("full_name", "User")), code)
    except requests.RequestException:
        delivered = False
    response = {"status": "success", "user_id": user_id, "verification_required": True, "email_delivery": "sent" if delivered else "not_configured"}
    if not delivered and os.getenv("AUTH_DEV_SHOW_VERIFICATION_CODE", "false").lower() == "true":
        response["development_verification_code"] = code
    return response


def _send_verification_email(email: str, name: str, code: str):
    key = os.getenv("BREVO_API_KEY")
    sender = os.getenv("AUTH_EMAIL_FROM")
    if not key or not sender:
        return False
    response = requests.post("https://api.brevo.com/v3/smtp/email", headers={"api-key": key, "content-type": "application/json"}, json={"sender": {"email": sender, "name": os.getenv("AUTH_EMAIL_FROM_NAME", "DisasterAI")}, "to": [{"email": email, "name": name}], "subject": "Verify your DisasterAI account", "htmlContent": f"<h2>DisasterAI verification</h2><p>Your verification code is <strong>{code}</strong>. It expires in 15 minutes.</p>"}, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return True


def verify_email(email: str, code: str):
    with _connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        if not row or not row["verification_hash"] or not hmac.compare_digest(_token_hash(code.strip()), row["verification_hash"]):
            raise ValueError("Invalid verification code")
        if datetime.fromisoformat(row["verification_expires_at"]) < _now():
            raise ValueError("Verification code has expired")
        status = "active" if row["role"] == "citizen" else "pending_approval"
        connection.execute("UPDATE users SET email_verified=1,status=?,verification_hash=NULL,verification_expires_at=NULL,updated_at=? WHERE id=?", (status, _now().isoformat(), row["id"]))
    return {"status": "success", "account_status": status}


def login_user(email: str, password: str):
    with _connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        if not row or not _password_valid(password, row["password_hash"]):
            raise ValueError("Incorrect email or password")
        if row["status"] != "active":
            raise PermissionError(row["status"])
        token = secrets.token_urlsafe(40)
        expires = _now() + timedelta(hours=int(os.getenv("AUTH_SESSION_HOURS", "24")))
        connection.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (_now().isoformat(),))
        connection.execute("INSERT INTO auth_sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)", (_token_hash(token), row["id"], expires.isoformat(), _now().isoformat()))
        return {"status": "success", "token": token, "expires_at": expires.isoformat(), "user": _public_user(row)}


def user_from_token(token: str):
    if not token:
        return None
    with _connect() as connection:
        row = connection.execute("SELECT users.* FROM auth_sessions JOIN users ON users.id=auth_sessions.user_id WHERE token_hash=? AND auth_sessions.expires_at>?", (_token_hash(token), _now().isoformat())).fetchone()
        return _public_user(row) if row else None


def logout_token(token: str):
    with _connect() as connection:
        connection.execute("DELETE FROM auth_sessions WHERE token_hash=?", (_token_hash(token),))


def list_pending_users():
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM users WHERE status='pending_approval' ORDER BY created_at").fetchall()
        return [_public_user(row) for row in rows]


def decide_user(user_id: int, approve: bool):
    status = "active" if approve else "rejected"
    with _connect() as connection:
        cursor = connection.execute("UPDATE users SET status=?,updated_at=? WHERE id=? AND status='pending_approval'", (status, _now().isoformat(), user_id))
        if not cursor.rowcount:
            raise ValueError("Pending account not found")
    return {"status": "success", "account_status": status}
