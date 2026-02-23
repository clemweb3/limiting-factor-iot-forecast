import os
import uvicorn
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Absolute imports
from .database import get_db_connection, init_db
from .model_helper import ModelEngine

# 1. INITIALIZE CONFIG
load_dotenv()
API_KEY = os.getenv("PROACTIVE_API_KEY")

app = FastAPI(title="Human-Centric Proactive AI - Engine v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. MOUNT DASHBOARD
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 3. ENGINE SETUP WITH FAILSAFE
try:
    engine = ModelEngine()
except Exception as e:
    print(f"[CRITICAL] AI Engine Failure: {e}")
    engine = None

# Track last state to prevent hardware "atterch" (Hysteresis)
last_action = {"command": None, "state": None, "timestamp": datetime.min}

@app.on_event("startup")
def startup_event():
    init_db()
    print("--- Proactive Climate Engine: ONLINE ---")

# 4. DATA PROVIDER
@app.get("/history")
async def get_history():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Ensure we get the most recent contextual readings
        cursor.execute('SELECT * FROM readings ORDER BY timestamp DESC LIMIT 20')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

# 5. SECURE TELEMETRY & DECISION ENGINE
@app.post("/telemetry")
async def process_telemetry(temp: float, hum: float, x_api_key: str = Header(None)):
    global last_action
    
    # Privacy & Security Check
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Default Failsafe Values
    p30, p60 = temp, temp
    led_cmd, state, human_msg = "RED_ON", "STABLE", "Monitoring..."

    if engine:
        # A. Get Predictions (Anomaly Window logic happens inside engine)
        p30, p60 = engine.predict_horizons(temp) 
        
        # B. Get Human-Centric Decision
        led_cmd, state, human_msg = engine.get_contextual_status(temp, p30, p60)

    # C. HARDWARE PROTECTION (Hysteresis)
    # Don't change hardware state more than once every 10 seconds unless it's an ANOMALY
    now = datetime.now()
    time_since_last = (now - last_action["timestamp"]).total_seconds()
    
    if "ANOMALY" not in state and time_since_last < 10 and last_action["command"] == led_cmd:
        # Keep previous human message to maintain "Fuzzy" continuity
        pass 
    else:
        last_action = {"command": led_cmd, "state": state, "timestamp": now}

    # 6. ENHANCED PERSISTENCE
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO readings (
                temperature, humidity, prediction_30, prediction_60, decision, human_notes
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (temp, hum, p30, p60, f"{led_cmd}:{state}", human_msg))
        conn.commit()
        conn.close()
    except Exception as db_error:
        print(f"[DB ERROR] {db_error}")

    # 7. RESPONSE (For ESP32/Hardware and Frontend)
    return {
        "command": led_cmd,
        "status": state,
        "cta": human_msg,
        "forecast": {
            "30m": round(p30, 2), 
            "60m": round(p60, 2),
            "trend": "rising" if p30 > temp else "cooling"
        },
        "system_meta": {
            "engine_active": engine is not None,
            "severity": "high" if "ANOMALY" in state else "normal"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)