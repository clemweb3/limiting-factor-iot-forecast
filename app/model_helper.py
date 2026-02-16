import joblib
import os
import pandas as pd
import random

# Absolute path for the model
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/sarima_thermal_model.pkl')

class ModelEngine:
    def __init__(self):
        self.THRESHOLD = 30.0
        # IMPROVEMENT: Anomaly detection threshold (degrees change per request)
        self.SPIKE_THRESHOLD = 2.0 
        self.last_temp = None
        
        if not os.path.exists(MODEL_PATH):
            print(f"[ERROR] Model file not found at {MODEL_PATH}")
            self.model = None
        else:
            self.model = joblib.load(MODEL_PATH)
            print("[AI] SARIMA Model Loaded Successfully")

    def predict_horizons(self, current_temp):
        """Calculates forecasts with an anomaly override logic."""
        # IMPROVEMENT: Detect Sudden Spikes (e.g., Fire/Sensor malfunction)
        if self.last_temp is not None:
            diff = current_temp - self.last_temp
            if diff > self.SPIKE_THRESHOLD:
                print(f"[ANOMALY] Sudden heat spike detected: +{diff}°C")
                # Override: If spike is extreme, predict even higher heat (Safeguard)
                return current_temp + 5.0, current_temp + 8.0
        
        self.last_temp = current_temp

        if not self.model:
            return 0.0, 0.0
        
        # SARIMA forecast
        forecast = self.model.forecast(steps=12)
        return float(forecast.iloc[5]), float(forecast.iloc[11])

    def _generate_script(self, scenario, eta=None):
        """IMPROVEMENT: Fuzzy/Varied messaging to avoid robot-like repetition."""
        scripts = {
            "ANOMALY": [
                "Extreme temperature spike detected! Safety protocols engaged.",
                "Abnormal heat rising rapidly. Disregarding normal forecast for safety.",
                "Warning: Sudden heat detected. Activating maximum cooling immediately."
            ],
            "PROACTIVE_COOLING": [
                f"I've detected energy rising; I'll engage the AC {eta} to keep you cool.",
                f"It's getting warmer. I'm prepping the cooling system for use {eta}.",
                f"Thermal trend is upward. I'll start the AC {eta} to maintain your comfort."
            ],
            "RECOVERY_MODE": [
                f"The heat is breaking. I'll switch off the fan {eta} to save energy.",
                f"Climate is cooling down. Fan shutdown scheduled {eta}.",
                f"Temperature is dropping back to normal. Disengaging fan {eta}."
            ],
            "STABLE": [
                "Environment is perfect. No changes needed for now.",
                "Climate is stable. I'm just monitoring the background trends.",
                "Everything looks good! Your room is staying within comfort levels."
            ]
        }
        return random.choice(scripts[scenario])

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
        time_str = f"in {eta} minutes" if eta and eta < 60 else "shortly"

        # 1. ANOMALY CHECK (Sudden Spike)
        if self.last_temp and (current - self.last_temp) > self.SPIKE_THRESHOLD:
            return "YELLOW_BLINK", "EMERGENCY_HEAT", self._generate_script("ANOMALY")

        # 2. SCENARIO: Rising Heat (Fuzzy Logic: Check both current and prediction)
        if p30 >= self.THRESHOLD:
            msg = self._generate_script("PROACTIVE_COOLING", time_str)
            # Check if we should turn on NOW or wait
            if current >= self.THRESHOLD:
                return "GREEN_ON", "ACTIVE_COOLING", f"Turning on the AC now to combat the heat. {msg}"
            return "YELLOW_BLINK", "PROACTIVE_PREP", msg
            
        # 3. SCENARIO: Currently Hot but Recovery is predicted
        elif current >= self.THRESHOLD and p30 < current:
            msg = self._generate_script("RECOVERY_MODE", time_str)
            return "GREEN_ON", "RECOVERY_MODE", msg

        # 4. SCENARIO: Stable
        else:
            return "RED_ON", "STABLE", self._generate_script("STABLE")