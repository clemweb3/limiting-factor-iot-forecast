import joblib
import os
import pandas as pd

# Path to the pre-trained SARIMA weights
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/sarima_thermal_model.pkl')

class ModelEngine:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model pkl not found at {MODEL_PATH}")
        self.model = joblib.load(MODEL_PATH)

    def predict_horizon(self, steps=12):
        """
        Generates forecast for the specified horizon.
        Default 12 steps = 60 minutes for 5-min sampled data.
        """
        forecast = self.model.forecast(steps=steps)
        # We return the end of the horizon for proactive control
        return float(forecast.iloc[-1])

    def get_decision(self, current, predicted):
        """
        Hybrid Logic: 
        RED: Idle | YELLOW: AI Transition | GREEN: Active
        """
        # Reactive Override (Heater Detection)
        if current >= 30.0:
            return "GREEN_ON", "REACTIVE_OVERRIDE"
        
        # Proactive Logic (SARIMA Trend)
        delta = predicted - current
        if delta >= 0.2:
            return "GREEN_ON", "PROACTIVE_ENGAGEMENT"
        elif 0.05 < delta < 0.2:
            return "YELLOW_BLINK", "AI_WARNING"
        else:
            return "RED_ON", "STABLE"