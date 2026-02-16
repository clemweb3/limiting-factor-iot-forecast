import os
import uvicorn
import asyncio # For future transition delays
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Absolute imports
from .database import get_db_connection, init_db
from .model_helper import ModelEngine

# 1. INITIALIZE CONFIG & SECURITY
load_dotenv()
# Make sure your .env has PROACTIVE_API_KEY or use the default below
API_KEY = os.getenv("PROACTIVE_API_KEY")

app = FastAPI(title="Human-Centric Proactive AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. MOUNT DASHBOARD STATIC FILES
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 3. ENGINE SETUP
try:
    engine = ModelEngine()
except Exception as e:
    print(f"[CRITICAL] AI Engine Failure: {e}")
    engine = None

@app.on_event("startup")
def startup_event():
    init_db()
    print("Proactive Climate Engine: ONLINE")

# 4. DATA PROVIDER (FOR THE HUMAN UI)
@app.get("/history")
async def get_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM readings ORDER BY timestamp DESC LIMIT 10')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# 5. SECURE TELEMETRY & CTA ENGINE
@app.post("/telemetry")
async def process_telemetry(temp: float, hum: float, x_api_key: str = Header(None)):
    # Privacy Check
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if engine:
        # IMPROVEMENT: Passing 'temp' to allow anomaly detection/spike checks
        p30, p60 = engine.predict_horizons(temp) 
        
        # IMPROVEMENT: Contextual status now handles anomaly states and varied scripts
        led_cmd, state, human_msg = engine.get_contextual_status(temp, p30, p60)
    else:
        p30, p60 = 0.0, 0.0
        led_cmd, state, human_msg = "RED_ON", "OFFLINE", "System offline. Operating in failsafe mode."

    # 6. PERSISTENCE
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

    # 7. RETURN TO CLIENT (ESP32 or Frontend)
    return {
        "command": led_cmd,
        "status": state,
        "cta": human_msg,
        "forecast": {"30m": round(p30, 2), "60m": round(p60, 2)}
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)