import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import requests

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # Local SQLite development does not require PostgreSQL.
    psycopg = None
    dict_row = None

INTEGRITY_ERRORS = (sqlite3.IntegrityError,) + ((psycopg.IntegrityError,) if psycopg else ())

from services.external_base import DEFAULT_TIMEOUT


DATA_DIR = os.getenv("DISASTER_DATA_DIR", "./data")
DB_PATH = os.path.join(DATA_DIR, "disaster_command.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USING_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))
PUBLIC_ROLES = {"citizen", "police", "fire", "rescue", "hospital"}


def _now():
    return datetime.now(timezone.utc)


def _connect():
    if USING_POSTGRES:
        if psycopg is None:
            raise RuntimeError("PostgreSQL driver is not installed")
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    os.makedirs(DATA_DIR, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _sql(query: str):
    return query.replace("?", "%s") if USING_POSTGRES else query


def _execute(connection, query: str, params=()):
    return connection.execute(_sql(query), params)


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
    if USING_POSTGRES:
        with _connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL,
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
                    updated_at TEXT NOT NULL,
                    UNIQUE(email, role)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
        _bootstrap_operator()
        return
    with _connect() as connection:
        legacy = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        migrate = bool(legacy and "email TEXT NOT NULL UNIQUE" in (legacy["sql"] or ""))
        if migrate:
            connection.execute("DROP TABLE IF EXISTS auth_sessions")
            connection.execute("ALTER TABLE users RENAME TO users_legacy")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE,
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
                updated_at TEXT NOT NULL,
                UNIQUE(email, role)
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """)
        if migrate:
            connection.execute("""INSERT INTO users(id,full_name,email,mobile,password_hash,role,location,official_details,status,email_verified,verification_hash,verification_expires_at,created_at,updated_at)
                SELECT id,full_name,email,mobile,password_hash,role,location,official_details,status,email_verified,verification_hash,verification_expires_at,created_at,updated_at FROM users_legacy""")
            connection.execute("DROP TABLE users_legacy")
    _bootstrap_operator()


def _bootstrap_operator():
    email = os.getenv("OPERATOR_EMAIL", "").strip().lower()
    password = os.getenv("OPERATOR_PASSWORD", "")
    if not email or len(password) < 10:
        return
    now = _now().isoformat()
    with _connect() as connection:
        existing = _execute(connection, "SELECT id FROM users WHERE role = 'operator'").fetchone()
        if existing:
            _execute(connection, "UPDATE users SET email=?, password_hash=?, status='active', email_verified=1, updated_at=? WHERE id=?", (email, _password_hash(password), now, existing["id"]))
        else:
            _execute(connection, "INSERT INTO users(full_name,email,password_hash,role,status,email_verified,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (os.getenv("OPERATOR_NAME", "System Operator"), email, _password_hash(password), "operator", "active", 1, now, now))


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
            insert_sql = """INSERT INTO users(full_name,email,mobile,password_hash,role,location,official_details,status,email_verified,verification_hash,verification_expires_at,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""" + (" RETURNING id" if USING_POSTGRES else "")
            cursor = _execute(connection, insert_sql, (str(payload.get("full_name", "")).strip(), email, str(payload.get("mobile", "")).strip(), _password_hash(password), role, str(payload.get("location", "")).strip(), json.dumps(payload.get("official_details") or {}), status, 0, _token_hash(code), (now + timedelta(minutes=15)).isoformat(), now.isoformat(), now.isoformat()))
            user_id = cursor.fetchone()["id"] if USING_POSTGRES else cursor.lastrowid
    except INTEGRITY_ERRORS as error:
        raise ValueError("This email already has an account for the selected department") from error
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


def verify_email(email: str, code: str, role: str):
    with _connect() as connection:
        row = _execute(connection, "SELECT * FROM users WHERE email=? AND role=?", (email.strip().lower(), role.strip().lower())).fetchone()
        if not row or not row["verification_hash"] or not hmac.compare_digest(_token_hash(code.strip()), row["verification_hash"]):
            raise ValueError("Invalid verification code")
        if datetime.fromisoformat(row["verification_expires_at"]) < _now():
            raise ValueError("Verification code has expired")
        status = "active" if row["role"] == "citizen" else "pending_approval"
        _execute(connection, "UPDATE users SET email_verified=1,status=?,verification_hash=NULL,verification_expires_at=NULL,updated_at=? WHERE id=?", (status, _now().isoformat(), row["id"]))
    return {"status": "success", "account_status": status}


def resend_verification(email: str, role: str):
    code = f"{secrets.randbelow(1_000_000):06d}"
    with _connect() as connection:
        row = _execute(connection, "SELECT * FROM users WHERE email=? AND role=? AND email_verified=0", (email.strip().lower(), role.strip().lower())).fetchone()
        if not row:
            raise ValueError("Unverified account not found")
        _execute(connection, "UPDATE users SET verification_hash=?,verification_expires_at=?,updated_at=? WHERE id=?", (_token_hash(code), (_now() + timedelta(minutes=15)).isoformat(), _now().isoformat(), row["id"]))
    delivered = _send_verification_email(row["email"], row["full_name"], code)
    return {"status": "success", "email_delivery": "sent" if delivered else "not_configured"}


def change_verification_email(old_email: str, new_email: str, role: str):
    new_email = new_email.strip().lower()
    if "@" not in new_email:
        raise ValueError("Enter a valid email address")
    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        with _connect() as connection:
            row = _execute(connection, "SELECT * FROM users WHERE email=? AND role=? AND email_verified=0", (old_email.strip().lower(), role.strip().lower())).fetchone()
            if not row:
                raise ValueError("Unverified account not found")
            _execute(connection, "UPDATE users SET email=?,verification_hash=?,verification_expires_at=?,updated_at=? WHERE id=?", (new_email, _token_hash(code), (_now() + timedelta(minutes=15)).isoformat(), _now().isoformat(), row["id"]))
    except INTEGRITY_ERRORS as error:
        raise ValueError("This email already has an account for the selected department") from error
    delivered = _send_verification_email(new_email, row["full_name"], code)
    return {"status": "success", "email_delivery": "sent" if delivered else "not_configured"}


def login_user(email: str, password: str, role: str = ""):
    with _connect() as connection:
        rows = _execute(connection, "SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchall()
        matches = [row for row in rows if _password_valid(password, row["password_hash"]) and (not role or row["role"] == role.strip().lower())]
        if not matches:
            raise ValueError("Incorrect email, password, or department")
        if len(matches) > 1:
            raise ValueError("Select the department you want to login to")
        row = matches[0]
        if row["status"] != "active":
            raise PermissionError(row["status"])
        token = secrets.token_urlsafe(40)
        expires = _now() + timedelta(hours=int(os.getenv("AUTH_SESSION_HOURS", "24")))
        _execute(connection, "DELETE FROM auth_sessions WHERE expires_at < ?", (_now().isoformat(),))
        _execute(connection, "INSERT INTO auth_sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)", (_token_hash(token), row["id"], expires.isoformat(), _now().isoformat()))
        return {"status": "success", "token": token, "expires_at": expires.isoformat(), "user": _public_user(row)}


def user_from_token(token: str):
    if not token:
        return None
    with _connect() as connection:
        row = _execute(connection, "SELECT users.* FROM auth_sessions JOIN users ON users.id=auth_sessions.user_id WHERE token_hash=? AND auth_sessions.expires_at>?", (_token_hash(token), _now().isoformat())).fetchone()
        return _public_user(row) if row else None


def logout_token(token: str):
    with _connect() as connection:
        _execute(connection, "DELETE FROM auth_sessions WHERE token_hash=?", (_token_hash(token),))


def list_pending_users():
    with _connect() as connection:
        rows = _execute(connection, "SELECT * FROM users WHERE status='pending_approval' ORDER BY created_at").fetchall()
        return [_public_user(row) for row in rows]


def list_department_users():
    """Return verified department accounts for the private operator directory."""
    with _connect() as connection:
        rows = _execute(connection,
            """SELECT * FROM users
               WHERE role IN ('citizen', 'police', 'fire', 'rescue', 'hospital')
                 AND email_verified=1
               ORDER BY role, full_name"""
        ).fetchall()
        return [_public_user(row) for row in rows]


def decide_user(user_id: int, approve: bool):
    status = "active" if approve else "rejected"
    with _connect() as connection:
        cursor = _execute(connection, "UPDATE users SET status=?,updated_at=? WHERE id=? AND status='pending_approval'", (status, _now().isoformat(), user_id))
        if not cursor.rowcount:
            raise ValueError("Pending account not found")
    return {"status": "success", "account_status": status}
