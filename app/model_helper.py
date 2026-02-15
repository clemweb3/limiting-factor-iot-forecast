import joblib
import os
import pandas as pd

# Absolute path for the model
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/sarima_thermal_model.pkl')

class ModelEngine:
    def __init__(self):
        self.THRESHOLD = 30.0
        if not os.path.exists(MODEL_PATH):
            print(f"[ERROR] Model file not found at {MODEL_PATH}")
            self.model = None
        else:
            self.model = joblib.load(MODEL_PATH)
            print("[AI] SARIMA Model Loaded Successfully")

    def predict_horizons(self):
        """Calculates 30-min (6 steps) and 60-min (12 steps) forecasts."""
        if not self.model:
            return 0.0, 0.0
        
        # SARIMA forecast
        forecast = self.model.forecast(steps=12)
        # index 5 = 30 mins, index 11 = 60 mins
        return float(forecast.iloc[5]), float(forecast.iloc[11])

    def calculate_eta(self, current, p30):
        delta_temp = p30 - current
        if abs(delta_temp) < 0.05: return None
        
        rate_per_min = delta_temp / 30
        
        if rate_per_min > 0: # Warming
            mins = (self.THRESHOLD - current) / rate_per_min
        else: # Cooling
            mins = (current - self.THRESHOLD) / abs(rate_per_min)
            
        return max(0, int(mins))

    def get_contextual_status(self, current, p30, p60):
        """Returns (command, state_label, human_message)"""
        eta = self.calculate_eta(current, p30)
        
        # SCENARIO 1: Rising Heat
        if p30 > current and p30 >= self.THRESHOLD:
            time_str = f"in {eta} minutes" if eta and eta < 60 else "shortly"
            msg = f"Thermal energy is rising. I will engage the AC {time_str} to maintain your comfort."
            cmd = "YELLOW_BLINK"
            state = "PROACTIVE_COOLING"
            
        # SCENARIO 2: Currently Hot but Cooling Down
        elif p30 < current and current >= self.THRESHOLD:
            time_str = f"in {eta} minutes" if eta and eta < 60 else "soon"
            msg = f"The heat is starting to break. I'll be able to switch off the FAN {time_str} to save energy."
            cmd = "GREEN_ON"
            state = "RECOVERY_MODE"

        # SCENARIO 3: Stable
        else:
            msg = "Climate is stable. No manual action or automated changes required for the next hour."
            cmd = "RED_ON"
            state = "STABLE"

        return cmd, state, msg