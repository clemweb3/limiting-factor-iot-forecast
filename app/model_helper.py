import joblib
import os
import pandas as pd
import random
from collections import deque

MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/sarima_thermal_model.pkl')

class ModelEngine:
    def __init__(self):
        self.THRESHOLD_UPPER = 30.0  # Heat limit
        self.THRESHOLD_LOWER = 18.0  # Cold limit
        
        # ANOMALY LOGIC: Derivative-based (Rate of Change)
        # We use a window to catch "Gradual" rises that are still too fast for reality
        self.temp_history = deque(maxlen=10) 
        self.SPIKE_THRESHOLD_HEAT = 1.5   # degrees per window
        self.SPIKE_THRESHOLD_COLD = -4.0  # degrees per window
        
        if not os.path.exists(MODEL_PATH):
            print(f"[ERROR] Model file not found at {MODEL_PATH}")
            self.model = None
        else:
            self.model = joblib.load(MODEL_PATH)
            print("[AI] SARIMA Model Loaded Successfully")

    def predict_horizons(self, current_temp):
        """Calculates forecasts with Moving-Window Anomaly Detection."""
        # Add to history for gradient analysis
        self.temp_history.append(current_temp)
        
        if len(self.temp_history) > 1:
            # Calculate gradient over the window (detects gradual but persistent rise)
            total_change = current_temp - self.temp_history[0]
            
            if total_change > self.SPIKE_THRESHOLD_HEAT:
                return current_temp + 4.0, current_temp + 7.0 # Proactive Safety Offset
            if total_change < self.SPIKE_THRESHOLD_COLD:
                return current_temp - 5.0, current_temp - 8.0

        if not self.model:
            return current_temp, current_temp
        
        try:
            forecast = self.model.forecast(steps=12)
            return float(forecast.iloc[5]), float(forecast.iloc[11])
        except:
            return current_temp, current_temp

    def _fuzzy_script_engine(self, category, severity_index, eta_str="shortly"):
        """
        REVISED: Semantic Scripting. 
        Instead of random, it selects based on Severity (0.0 to 1.0)
        """
        scripts = {
            "HEAT_ANOMALY": {
                "high": "CRITICAL: Extreme thermal rise. Overriding systems for maximum cooling.",
                "low": "Thermal drift detected. Increasing cooling intensity proactively."
            },
            "COLD_ANOMALY": {
                "high": "CRITICAL: Sudden temperature drop. Disengaging fans to preserve heat.",
                "low": "Unusual cooling detected. Adjusting energy protocols."
            },
            "PROACTIVE_COOL": [
                f"Trend is upward. I'll engage cooling {eta_str} to stay ahead of the heat.",
                f"Forecasting a warm shift. Preparing the AC for use {eta_str}."
            ],
            "STABLE": [
                "Environment is balanced. Monitoring background fluctuations.",
                "Climate parameters nominal. No intervention required."
            ]
        }

        # Logic for selection
        if "ANOMALY" in category:
            lvl = "high" if severity_index > 0.7 else "low"
            return scripts[category][lvl]
        
        return random.choice(scripts.get(category, scripts["STABLE"]))

    def get_contextual_status(self, current, p30, p60):
        """Returns (command, state_label, human_message)"""
        
        # Calculate Severity for Fuzzy Logic
        heat_severity = max(0, (current - self.THRESHOLD_UPPER) / 5.0)
        
        # 1. DETECT THERMAL DIVERGENCE (Window-based)
        if len(self.temp_history) >= 2:
            change = current - self.temp_history[0]
            
            # HEAT PATHWAY
            if change > self.SPIKE_THRESHOLD_HEAT:
                msg = self._fuzzy_script_engine("HEAT_ANOMALY", heat_severity)
                return "YELLOW_BLINK", "ANOMALY_HEAT", msg
            
            # COLD PATHWAY
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

        # 4. STABLE
        return "RED_ON", "STABLE", self._fuzzy_script_engine("STABLE", 0)