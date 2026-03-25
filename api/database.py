import sqlite3
import bcrypt
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'quantumshield.db')

def get_connection():
    """Get a SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _column_exists(cur, table, column):
    """Check if a column exists in a table (for migrations)."""
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def init_db(database_url=None):
    """Initialize database tables if they don't exist, and migrate existing ones."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── Create users table ─────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    cur.execute("SELECT id FROM users WHERE email = ?", ('admin@gmail.com',))
    if not cur.fetchone():
        admin_hash = bcrypt.hashpw('admin@123'.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
        cur.execute("""
            INSERT INTO users (name, email, password_hash, role, is_face_verified, face_attributes_json)
            VALUES (?, ?, ?, 'admin', 1, '{}')
        """, ('Admin', 'admin@gmail.com', admin_hash))
        print("[DB] Admin user seeded: admin@gmail.com / admin@123")

    conn.commit()
    conn.close()
    print(f"[DB] SQLite database ready at: {DB_PATH}")
