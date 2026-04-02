import psycopg2
import psycopg2.extras
import bcrypt
import os
from urllib.parse import urlparse

# PostgreSQL connection URL — set via environment variable or use default
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:1234@localhost:5432/quantumshield'
)


def _ensure_database_exists(url=None):
    """Auto-create the PostgreSQL database if it doesn't exist."""
    url = url or DATABASE_URL
    parsed = urlparse(url)
    db_name = parsed.path.lstrip('/')  # e.g. 'quantumshield'

    # Connect to default 'postgres' database to check/create ours
    admin_url = f"{parsed.scheme}://{parsed.netloc}/postgres"
    try:
        conn = psycopg2.connect(admin_url)
        conn.autocommit = True  # CREATE DATABASE can't run inside a transaction
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{db_name}"')
            print(f"[DB] Created PostgreSQL database: {db_name}")
        conn.close()
    except Exception as e:
        print(f"[DB] Could not auto-create database (may already exist): {e}")


def get_connection():
    """Get a PostgreSQL database connection."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def _get_cursor(conn):
    """Return a cursor that returns rows as dicts."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def _column_exists(cur, table, column):
    """Check if a column exists in a table (for migrations)."""
    cur.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return cur.fetchone() is not None


def init_db(database_url=None):
    """Initialize database tables if they don't exist, and migrate existing ones."""
    url = database_url or DATABASE_URL

    # Auto-create the database if it doesn't exist
    _ensure_database_exists(url)

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    # ── Create users table ─────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT DEFAULT '',
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            is_blocked INTEGER DEFAULT 0,
            registered_device TEXT DEFAULT '',
            home_city TEXT DEFAULT '',
            home_country TEXT DEFAULT '',
            avg_typing_speed REAL DEFAULT 0.0,
            typing_variance REAL DEFAULT 0.0,
            login_count INTEGER DEFAULT 0,
            face_embedding TEXT DEFAULT '',
            face_attributes_json TEXT DEFAULT '{}',
            is_face_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Migration: add columns to users if upgrading existing DB ───
    users_migrations = [
        ("name", "TEXT DEFAULT ''"),
        ("face_attributes_json", "TEXT DEFAULT '{}'"),
    ]
    for col, col_def in users_migrations:
        if not _column_exists(cur, 'users', col):
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
            print(f"[DB] Migrated users: added column '{col}'")

    # ── Create login_logs table ────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            email TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            device_info TEXT DEFAULT '',
            city TEXT DEFAULT '',
            country TEXT DEFAULT '',
            latitude REAL DEFAULT 0.0,
            longitude REAL DEFAULT 0.0,
            typing_speed REAL DEFAULT 0.0,
            device_risk REAL DEFAULT 0.0,
            location_risk REAL DEFAULT 0.0,
            behavior_risk REAL DEFAULT 0.0,
            face_risk REAL DEFAULT 0.0,
            total_risk REAL DEFAULT 0.0,
            decision TEXT DEFAULT 'ALLOW',
            face_verdict TEXT DEFAULT '',
            face_confidence REAL DEFAULT 0.0,
            face_image_path TEXT DEFAULT '',
            is_suspicious INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Migration: add columns to login_logs if upgrading existing DB ─
    logs_migrations = [
        ("face_image_path", "TEXT DEFAULT ''"),
        ("latitude", "REAL DEFAULT 0.0"),
        ("longitude", "REAL DEFAULT 0.0"),
        ("is_suspicious", "INTEGER DEFAULT 0"),
    ]
    for col, col_def in logs_migrations:
        if not _column_exists(cur, 'login_logs', col):
            cur.execute(f"ALTER TABLE login_logs ADD COLUMN {col} {col_def}")
            print(f"[DB] Migrated login_logs: added column '{col}'")

    # ── Seed admin user if not exists ──────────────────────────────
    cur.execute("SELECT id FROM users WHERE email = %s", ('admin@quantumshield.io',))
    if not cur.fetchone():
        # Password: QS@dmin2024!
        admin_hash = bcrypt.hashpw('QS@dmin2024!'.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
        cur.execute("""
            INSERT INTO users (name, email, password_hash, role, is_face_verified, face_attributes_json)
            VALUES (%s, %s, %s, 'admin', 1, '{}')
        """, ('System Administrator', 'admin@quantumshield.io', admin_hash))
        print("[DB] Admin user seeded: admin@quantumshield.io / QS@dmin2024!")

    conn.commit()
    conn.close()
    print(f"[DB] PostgreSQL database ready at: {url}")
