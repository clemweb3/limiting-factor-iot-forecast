import os
import uvicorn
import random
import math
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import get_db_connection, init_db
from .model_helper import ModelEngine

# ──────────────────────────────────────────────
#  CozySense FastAPI Gateway v3
#  Fixes applied:
#   [1] Hysteresis now correctly preserves DB-written state
#   [2] /simulate endpoint for public demo (no auth required)
#   [3] /status public read endpoint (no auth required)
#   [4] /history returns richer payload for frontend sparkline
# ──────────────────────────────────────────────

load_dotenv()
API_KEY = os.getenv("PROACTIVE_API_KEY", "dev-key-change-me")

app = FastAPI(
    title="CozySense — Proactive Climate Engine",
    description="Hybrid SARIMA + Heuristic edge inference with semantic XAI output.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── Engine Bootstrap ───────────────────────────────────────────────────────
try:
    engine = ModelEngine()
    print("[Gateway] ModelEngine initialized.")
except Exception as e:
    print(f"[CRITICAL] ModelEngine failed: {e}")
    engine = None

# ── Hysteresis State (FIX [1]: now tracks full persisted payload) ──────────
last_persisted = {
    "command":    None,
    "state":      None,
    "human_msg":  None,
    "timestamp":  datetime.min
}

HYSTERESIS_SECONDS = 10  # Minimum interval between hardware state changes


@app.on_event("startup")
def startup_event():
    init_db()
    print("─── CozySense Climate Engine: ONLINE ───")


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS (No auth required — safe for GitHub Pages frontend)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/status", tags=["Public"])
async def get_status():
    """
    Returns the most recent inference result.
    Safe for public consumption — no raw sensor data exposed.
    Used by GitHub Pages frontend to poll current state.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT timestamp, temperature, prediction_30, prediction_60, decision, human_notes '
            'FROM readings ORDER BY timestamp DESC LIMIT 1'
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return {"status": "no_data", "message": "Awaiting first telemetry reading."}

        cmd, state = row["decision"].split(":") if ":" in row["decision"] else ("RED_ON", "STABLE")
        return {
            "timestamp":    row["timestamp"],
            "temperature":  row["temperature"],
            "forecast_30m": row["prediction_30"],
            "forecast_60m": row["prediction_60"],
            "command":      cmd,
            "state":        state,
            "cta":          row["human_notes"],
            "trend":        "rising" if row["prediction_30"] > row["temperature"] else "cooling"
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/history", tags=["Public"])
async def get_history(limit: int = Query(default=20, le=100)):
    """
    Returns recent readings for the frontend sparkline chart.
    Ordered oldest→newest for chart rendering.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, timestamp, temperature, humidity, prediction_30, prediction_60, '
            'decision, human_notes FROM readings ORDER BY timestamp DESC LIMIT ?',
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        # Reverse so chart renders left→right chronologically
        return list(reversed([dict(row) for row in rows]))
    except Exception as e:
        return {"error": str(e)}


@app.get("/simulate", tags=["Public Demo"])
async def simulate_scenario(scenario: str = Query(default="stable")):
    """
    Injects a synthetic telemetry reading for public demo mode.
    No API key required. Scenarios:
      - stable         : Normal afternoon (25–26°C)
      - morning_rise   : Gradual diurnal rise (22→27°C over time)
      - thermal_shock  : Sudden heat spike (triggers anomaly path)
      - cold_event     : Rapid cooling (AC turned on hard)
      - proactive      : Temperature approaching threshold (triggers PROACTIVE_PREP)
    """
    scenario_params = {
        "stable":        {"base": 25.0, "noise": 0.3, "hum": 60.0},
        "morning_rise":  {"base": 22.0, "noise": 0.5, "hum": 65.0},
        "thermal_shock": {"base": 29.5, "noise": 0.2, "hum": 55.0},
        "cold_event":    {"base": 17.5, "noise": 0.4, "hum": 70.0},
        "proactive":     {"base": 28.0, "noise": 0.3, "hum": 58.0},
    }

    params = scenario_params.get(scenario, scenario_params["stable"])
    noise = random.gauss(0, params["noise"])
    temp = round(params["base"] + noise, 2)
    hum  = round(params["hum"] + random.gauss(0, 1.5), 2)

    return await _process_reading(temp, hum)


# ═══════════════════════════════════════════════════════════════════════════
#  SECURE TELEMETRY ENDPOINT (ESP32 / Hardware)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/telemetry", tags=["Hardware"])
async def process_telemetry(
    temp: float,
    hum: float,
    x_api_key: str = Header(None)
):
    """
    Authenticated sensor ingestion endpoint.
    Called by ESP32/DHT22. Requires X-API-Key header.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    return await _process_reading(temp, hum)


# ═══════════════════════════════════════════════════════════════════════════
#  SHARED INFERENCE CORE
#  FIX [1]: Hysteresis correctly gates both DB write AND response payload.
# ═══════════════════════════════════════════════════════════════════════════

async def _process_reading(temp: float, hum: float) -> dict:
    """
    Shared inference pipeline used by both /telemetry and /simulate.
    Handles prediction, fuzzy inference, hysteresis, and persistence.
    """
    global last_persisted

    # ── Default failsafe ───────────────────────────────────────────────────
    p30, p60 = temp, temp
    led_cmd, state, human_msg = "RED_ON", "STABLE", "Monitoring..."

    if engine:
        p30, p60     = engine.predict_horizons(temp)
        led_cmd, state, human_msg = engine.get_contextual_status(temp, p30, p60)

    # ── Hysteresis gate ────────────────────────────────────────────────────
    now = datetime.now()
    time_since_last = (now - last_persisted["timestamp"]).total_seconds()
    is_anomaly = "ANOMALY" in state

    # Only update persisted state if:
    #   - It's an anomaly (always propagate immediately), OR
    #   - Enough time has elapsed AND the command has changed
    should_update = (
        is_anomaly or
        time_since_last >= HYSTERESIS_SECONDS or
        last_persisted["command"] != led_cmd
    )

    if should_update:
        last_persisted = {
            "command":   led_cmd,
            "state":     state,
            "human_msg": human_msg,
            "timestamp": now
        }
    else:
        # Preserve the last stable state — don't thrash LED/hardware
        led_cmd   = last_persisted["command"]
        state     = last_persisted["state"]
        human_msg = last_persisted["human_msg"]

    # ── Persistence (DB write uses resolved state, not raw computed state) ─
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO readings
               (temperature, humidity, prediction_30, prediction_60, decision, human_notes)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (temp, hum, p30, p60, f"{led_cmd}:{state}", human_msg)
        )
        conn.commit()
        conn.close()
    except Exception as db_error:
        print(f"[DB ERROR] {db_error}")

    # ── Response ───────────────────────────────────────────────────────────
    return {
        "command": led_cmd,
        "status":  state,
        "cta":     human_msg,
        "forecast": {
            "30m":   p30,
            "60m":   p60,
            "trend": "rising" if p30 > temp else "cooling"
        },
        "sensor": {
            "temperature": temp,
            "humidity":    hum
        },
        "system_meta": {
            "engine_active": engine is not None,
            "severity":      "high" if is_anomaly else "normal",
            "timestamp":     now.isoformat()
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)