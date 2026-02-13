import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Absolute imports based on your structure
from .database import get_db_connection, init_db
from .model_helper import ModelEngine

# 1. LOAD CONFIGURATION
# This pulls the PROACTIVE_API_KEY from your .env file
load_dotenv()
API_KEY = os.getenv("PROACTIVE_API_KEY")

app = FastAPI(title="Edge-Driven Proactive API")

# 2. SECURITY: CORS (Cross-Origin Resource Sharing)
# This allows your index.html to talk to your API safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the ML Inference Engine
try:
    engine = ModelEngine()
except Exception as e:
    print(f"[CRITICAL] AI Engine failed to start: {e}")
    engine = None

# 3. LIFECYCLE MANAGEMENT
@app.on_event("startup")
def startup_event():
    """Triggers when the server starts - ensures DB exists."""
    init_db()
    print("Proactive Climate Server is LIVE")

# 4. SECURE TELEMETRY ENDPOINT
@app.post("/telemetry")
async def process_telemetry(temp: float, hum: float, x_api_key: str = Header(None)):
    """
    Main ingestion point for ESP32.
    Validates API Key before processing ML logic.
    """
    # Credential Validation
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")

    # ML Inference Step
    # We predict the next 60 minutes based on current sensor input
    if engine:
        predicted_temp = engine.predict_horizon(steps=12)
        led_state, reason = engine.get_decision(temp, predicted_temp)
    else:
        # Fallback to reactive logic if model fails
        predicted_temp = 0.0
        led_state, reason = ("GREEN_ON" if temp >= 30.0 else "RED_ON"), "MODEL_OFFLINE"

    # Persistence Step
    # Logging the interaction into the SQL database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO readings (temperature, humidity, prediction, decision)
            VALUES (?, ?, ?, ?)
        ''', (temp, hum, predicted_temp, f"{led_state}:{reason}"))
        conn.commit()
        conn.close()
    except Exception as db_error:
        print(f"[DB ERROR] {db_error}")

    return {
        "command": led_state,
        "prediction": round(predicted_temp, 2),
        "reason": reason,
        "timestamp": "recorded"
    }

# 5. SERVER RUNTIME
if __name__ == "__main__":
    # Runs the server on port 8000
    # Use 0.0.0.0 to make it accessible to ESP32 on the same Wi-Fi
    uvicorn.run(app, host="0.0.0.0", port=8000)