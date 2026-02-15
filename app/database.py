import sqlite3
import os

# 1. PATH CONFIGURATION
# Using absolute paths ensures the .db file stays in the /app folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'iot_data.db')

def get_db_connection():
    """Returns a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Crucial for accessing columns by name
    return conn

def init_db():
    """Initializes the database schema with human-centric AI columns."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 2. SCHEMA DEFINITION
    # We expanded this to accommodate Dual-Horizon and Human Personality notes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            prediction_30 REAL,   -- Prediction for the 30-min horizon
            prediction_60 REAL,   -- Prediction for the 60-min horizon
            decision TEXT,        -- The LED command and State (e.g., 'YELLOW_BLINK:WARMING')
            human_notes TEXT      -- The 'Personality' text for the Dashboard
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[DB] System fully initialized at: {DB_PATH}")

if __name__ == "__main__":
    init_db()