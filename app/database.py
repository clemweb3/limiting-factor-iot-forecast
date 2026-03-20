import sqlite3
import os
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
#  CozySense Database Layer v3
# ──────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'iot_data.db')


def get_db_connection() -> sqlite3.Connection:
    """
    Returns an optimized SQLite connection.
    WAL mode: allows concurrent reads during writes (critical for IoT throughput).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=-8000')   # 8MB page cache
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes schema. Safe to call on every startup (IF NOT EXISTS guards).
    Adds severity column population via a computed insert trigger.
    """
    conn   = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature   REAL NOT NULL,
            humidity      REAL NOT NULL,
            prediction_30 REAL,
            prediction_60 REAL,
            decision      TEXT,
            severity      TEXT DEFAULT 'NORMAL',
            human_notes   TEXT
        )
    ''')

    # Index for fast timestamp-ordered queries (frontend history poll)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON readings (timestamp)')

    # Index for severity filtering (anomaly audit log)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_severity ON readings (severity)')

    conn.commit()
    conn.close()
    print(f"[DB] Initialized at: {DB_PATH}")


def prune_old_data(days_to_keep: int = 7):
    """
    Housekeeping: prunes records older than N days.
    Keeps the DB small for long-running edge deployments.
    Call this from a scheduled task or on startup.
    """
    try:
        conn    = get_db_connection()
        cursor  = conn.cursor()
        cutoff  = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('DELETE FROM readings WHERE timestamp < ?', (cutoff,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        if deleted > 0:
            print(f"[DB Prune] Removed {deleted} records older than {days_to_keep} days.")
    except Exception as e:
        print(f"[DB ERROR] Prune failed: {e}")


def get_anomaly_log(limit: int = 50) -> list:
    """
    Returns recent anomaly events for audit/debug dashboard.
    """
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM readings WHERE severity != 'NORMAL' ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[DB ERROR] Anomaly log failed: {e}")
        return []


if __name__ == "__main__":
    init_db()
