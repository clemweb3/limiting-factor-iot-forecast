import joblib
import os
import pandas as pd

# --- DIRECTORY CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, '../models/sarima_thermal_model.pkl')

def get_proactive_command(current_temp, predicted_temp):
    """
    Architectural Logic for Smart Cooling (Philippines Context)
    RED: Idle | YELLOW: AI Warning | GREEN: Cooling Active
    """
    # 1. IMMEDIATE HEATER OVERRIDE (Reactive)
    if current_temp >= 30.0:
        return "COMMAND:GREEN_ON (REACTIVE_COOLING_MAX)"

    # 2. PREDICTIVE LOGIC (Proactive)
    delta = predicted_temp - current_temp

    if delta >= 0.2:
        return "COMMAND:GREEN_ON (PROACTIVE_COOLING_START)"
    elif 0.05 < delta < 0.2:
        return "COMMAND:YELLOW_BLINK (AI_PREDICTING_HEAT_RISE)"
    else:
        return "COMMAND:RED_ON (SYSTEM_IDLE_SAVING_ENERGY)"

def run_pipeline():
    print("\n" + "="*50)
    print("PROACTIVE CLIMATE CONTROL: ARCHITECTURAL PIPELINE")
    print("="*50)

    if not os.path.exists(MODEL_PATH):
        print("[ERROR] Model file not found. Ensure Notebook 02 is complete.")
        return

    # Load "Frozen Brain"
    model = joblib.load(MODEL_PATH)
    
    # Test Scenario: 28.0C current, checking 60-min horizon
    current = 28.0
    forecast = model.forecast(steps=12) 
    predicted = forecast.iloc[-1]

    print(f"Current Environment: {current}°C")
    print(f"AI Forecast (1h):   {predicted:.2f}°C")
    print(f"Decision Output:     {get_proactive_command(current, predicted)}")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_pipeline()