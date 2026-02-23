import sqlite3
import os
from datetime import datetime, timedelta

# 1. PATH CONFIGURATION
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'iot_data.db')

def get_db_connection():
    """Returns a connection with optimized PRAGMAS for IoT performance."""
    conn = sqlite3.connect(DB_PATH)
    # Performance Optimization: WAL mode allows simultaneous reads and writes
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes schema with indexing and severity tracking."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 2. SCHEMA DEFINITION (Enhanced)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            prediction_30 REAL,
            prediction_60 REAL,
            decision TEXT,        -- Format: 'CMD:STATE'
            severity TEXT DEFAULT 'NORMAL', -- 'NORMAL', 'WARNING', 'CRITICAL'
            human_notes TEXT
        )
    ''')
    
    # 3. INDEXING (Crucial for UI speed)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON readings (timestamp)')
    
    conn.commit()
    conn.close()
    print(f"[DB] Optimized System Initialized at: {DB_PATH}")

def prune_old_data(days_to_keep=7):
    """
    HOUSEKEEPING: Keeps the database small and fast.
    Deletes records older than the specified days.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('DELETE FROM readings WHERE timestamp < ?', (cutoff,))
        conn.commit()
        deleted_count = cursor.rowcount
        conn.close()
        if deleted_count > 0:
            print(f"[DB CLEANUP] Pruned {deleted_count} old records.")
    except Exception as e:
        print(f"[DB ERROR] Cleanup failed: {e}")

if __name__ == "__main__":
    init_db()