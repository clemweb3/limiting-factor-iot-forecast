import joblib
import os
import pandas as pd
import random
from collections import deque

MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/sarima_thermal_model.pkl')

class ModelEngine:
    def __init__(self):
        # Fuzzy Set Bounds (Linguistic Variables)
        self.COLD_VALLEY = 18.0
        self.STABLE_COMFORT = 24.0
        self.WARM_THRESHOLD = 27.0
        self.HOT_LIMIT = 30.0
        
        self.temp_history = deque(maxlen=10) 
        self.SPIKE_THRESHOLD_HEAT = 1.5   
        self.SPIKE_THRESHOLD_COLD = -4.0  
        
        # Model Loading Logic
        if not os.path.exists(MODEL_PATH):
            self.model = None
        else:
            try:
                self.model = joblib.load(MODEL_PATH)
            except:
                self.model = None

    # --- FUZZY MEMBERSHIP FUNCTIONS (The "XAI" Core) ---
    def _mu_heat(self, temp):
        """Degree of 'Heat' membership."""
        if temp <= self.WARM_THRESHOLD: return 0.0
        if temp >= self.HOT_LIMIT: return 1.0
        return (temp - self.WARM_THRESHOLD) / (self.HOT_LIMIT - self.WARM_THRESHOLD)

    def _mu_anomaly(self, delta, limit):
        """Degree of 'Anomaly' severity based on rate of change."""
        abs_delta = abs(delta)
        abs_limit = abs(limit)
        if abs_delta < abs_limit: return 0.0
        # Scale severity between limit and a 'critical' jump of 5 degrees
        return min(1.0, (abs_delta - abs_limit) / (5.0 - abs_limit))

    def predict_horizons(self, current_temp):
        self.temp_history.append(current_temp)
        p30, p60 = current_temp, current_temp
        
        if self.model:
            try:
                forecast = self.model.forecast(steps=12)
                p30, p60 = float(forecast.iloc[5]), float(forecast.iloc[11])
            except: pass

        if len(self.temp_history) > 1:
            total_change = current_temp - self.temp_history[0]
            if total_change > self.SPIKE_THRESHOLD_HEAT:
                p30 += 3.5; p60 += 6.0
            elif total_change < self.SPIKE_THRESHOLD_COLD:
                p30 -= 4.5; p60 -= 7.0

        return p30, p60

    def _fuzzy_script_engine(self, category, mu, eta_str="shortly"):
        """Defuzzification: Converts degree (mu) into linguistic scripts."""
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
                f"Trend is upward (Confidence: {mu:.1%}). Engaging cooling {eta_str}.",
                f"Warm shift forecasted. Preparing the AC {eta_str}."
            ],
            "STABLE": [
                "Environment is balanced. Monitoring background fluctuations.",
                "Atmospheric stability maintained. System in watch-mode."
            ]
        }

        if "ANOMALY" in category:
            lvl = "high" if mu > 0.7 else "low"
            return scripts[category][lvl]
        
        if category == "PROACTIVE_COOL":
            return random.choice(scripts[category])
            
        return random.choice(scripts["STABLE"])

    def get_contextual_status(self, current, p30, p60):
        """Fuzzy Inference Engine: Maps inputs to Semantic Outputs."""
        
        # 1. ANOMALY INFERENCE (High Priority)
        if len(self.temp_history) >= 2:
            change = current - self.temp_history[0]
            
            if change > self.SPIKE_THRESHOLD_HEAT:
                mu_a = self._mu_anomaly(change, self.SPIKE_THRESHOLD_HEAT)
                return "YELLOW_BLINK", "ANOMALY_HEAT", self._fuzzy_script_engine("HEAT_ANOMALY", mu_a)
            
            if change < self.SPIKE_THRESHOLD_COLD:
                mu_a = self._mu_anomaly(change, self.SPIKE_THRESHOLD_COLD)
                return "BLUE_BLINK", "ANOMALY_COLD", self._fuzzy_script_engine("COLD_ANOMALY", mu_a)

        # 2. PROACTIVE/ACTIVE INFERENCE (Fuzzy Heat sets)
        mu_curr = self._mu_heat(current)
        mu_p30 = self._mu_heat(p30)

        # If current is already HOT (mu=1.0)
        if mu_curr >= 1.0:
            return "GREEN_ON", "ACTIVE_COOLING", f"Threshold reached. {self._fuzzy_script_engine('STABLE', 0)}"

        # If current is STABLE but forecast is WARMING (Fuzzy Proactive Trigger)
        if mu_p30 > 0.4:
            return "YELLOW_BLINK", "PROACTIVE_PREP", self._fuzzy_script_engine("PROACTIVE_COOL", mu_p30, "in 20m")

        # 3. ECONOMY INFERENCE
        if current <= self.COLD_VALLEY:
            return "BLUE_ON", "ECONOMY_MODE", "Temp is low. Disengaging appliances to save power."

        # 4. DEFAULT STABLE
        return "RED_ON", "STABLE", self._fuzzy_script_engine("STABLE", 0)