import joblib
import os
import pandas as pd

# 1. IMMEDIATE FEEDBACK
print("\n" + "="*40)
print("ARCHITECTURAL PIPELINE: START")
print("="*40)

# 2. PATH SETUP (Absolute Logic)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, '../models/sarima_thermal_model.pkl')

print(f"Targeting Model at: {MODEL_PATH}")

# 3. EXECUTION
if not os.path.exists(MODEL_PATH):
    print(f"[FAIL] Model file not found! Check your /models folder.")
else:
    try:
        # Load the "Brain"
        model = joblib.load(MODEL_PATH)
        print("[SUCCESS] SARIMA Model Loaded into Memory.")

        # Simulate a reading
        mock_temp = 28.0
        # Get a forecast (steps=12 is 60 minutes)
        forecast = model.forecast(steps=12)
        predicted_temp = forecast.iloc[-1]

        print(f"\n--- INFERENCE RESULTS ---")
        print(f"Current Temp:   {mock_temp}°C")
        print(f"Predicted (1h): {predicted_temp:.2f}°C")
        
        # Command Logic
        if predicted_temp > mock_temp + 0.15:
            print("DECISION:       COMMAND:1 (Proactive Fan ON)")
        else:
            print("DECISION:       COMMAND:0 (System Stable)")
            
    except Exception as e:
        print(f"[ERROR] Logic failed: {e}")

print("="*40)
print("ARCHITECTURAL PIPELINE: END")
print("="*40 + "\n")