import joblib
import os
import pandas as pd
import random
from collections import deque

MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/sarima_thermal_model.pkl')

class ModelEngine:
    def __init__(self):
        self.THRESHOLD_UPPER = 30.0
        self.THRESHOLD_LOWER = 18.0
        
        self.temp_history = deque(maxlen=10) 
        self.SPIKE_THRESHOLD_HEAT = 1.5   
        self.SPIKE_THRESHOLD_COLD = -4.0  
        
        if not os.path.exists(MODEL_PATH):
            print(f"[ERROR] Model file not found at {MODEL_PATH}")
            self.model = None
        else:
            try:
                self.model = joblib.load(MODEL_PATH)
                print("[AI] SARIMA Model Loaded Successfully")
            except:
                self.model = None

    def predict_horizons(self, current_temp):
        """Calculates forecasts, injecting Anomaly Momentum if detected."""
        self.temp_history.append(current_temp)
        
        # Default: Base SARIMA Prediction
        p30, p60 = current_temp, current_temp
        if self.model:
            try:
                forecast = self.model.forecast(steps=12)
                p30, p60 = float(forecast.iloc[5]), float(forecast.iloc[11])
            except: pass

        # ANOMALY AMPLIFICATION: Don't override SARIMA, ADD to it.
        if len(self.temp_history) > 1:
            total_change = current_temp - self.temp_history[0]
            
            if total_change > self.SPIKE_THRESHOLD_HEAT:
                # Add momentum to the existing forecast
                p30 += 3.5
                p60 += 6.0
            elif total_change < self.SPIKE_THRESHOLD_COLD:
                p30 -= 4.5
                p60 -= 7.0

        return p30, p60

    def _fuzzy_script_engine(self, category, severity_index, eta_str="shortly"):
        scripts = {
            "HEAT_ANOMALY": {
                "high": "CRITICAL: Extreme thermal rise. Overriding systems for maximum cooling.",
                "low": "Thermal drift detected. Increasing cooling intensity proactively."
            },
            "COLD_ANOMALY": {
                "high": "CRITICAL: Sudden temperature drop. Disengaging hardware to preserve heat.",
                "low": "Unusual cooling detected. Adjusting energy protocols."
            },
            "PROACTIVE_COOL": [
                f"Trend is upward. I'll engage cooling {eta_str} to stay ahead of the heat.",
                f"Forecasting a warm shift. Preparing the AC for use {eta_str}."
            ],
            "STABLE": [
                "Environment is balanced. Monitoring background fluctuations.",
                "Climate parameters nominal. No intervention required.",
                "Atmospheric stability maintained. System in watch-mode."
            ]
        }

        if "ANOMALY" in category:
            lvl = "high" if severity_index > 0.7 else "low"
            return scripts[category][lvl]
        
        return random.choice(scripts.get(category, scripts["STABLE"]))

    def get_contextual_status(self, current, p30, p60):
        """Returns (command, state_label, human_message)"""
        
        # 1. ANOMALY DETECTION (Highest Priority)
        if len(self.temp_history) >= 2:
            change = current - self.temp_history[0]
            
            if change > self.SPIKE_THRESHOLD_HEAT:
                sev = min(1.0, change / 5.0)
                return "YELLOW_BLINK", "ANOMALY_HEAT", self._fuzzy_script_engine("HEAT_ANOMALY", sev)
            
            if change < self.SPIKE_THRESHOLD_COLD:
                return "BLUE_BLINK", "ANOMALY_COLD", self._fuzzy_script_engine("COLD_ANOMALY", 1.0)

        # 2. PROACTIVE SARIMA LOGIC (Steady State)
        if p30 >= self.THRESHOLD_UPPER:
            msg = self._fuzzy_script_engine("PROACTIVE_COOL", 0, "in 20m")
            if current >= self.THRESHOLD_UPPER:
                return "GREEN_ON", "ACTIVE_COOLING", f"Threshold exceeded. {msg}"
            return "YELLOW_BLINK", "PROACTIVE_PREP", msg

        # 3. COLD CONTEXT
        if current <= self.THRESHOLD_LOWER:
            return "BLUE_ON", "ECONOMY_MODE", "Temp is low. Disengaging appliances to save power."

        # 4. STABLE (Default)
        return "RED_ON", "STABLE", self._fuzzy_script_engine("STABLE", 0)