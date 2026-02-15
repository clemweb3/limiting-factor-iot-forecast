import joblib
import os
import random

class ModelEngine:
    def __init__(self):
        # ... (loading model code) ...
        self.THRESHOLD = 30.0  # Your comfort limit

    def calculate_eta(self, current, p30):
        """Calculates minutes remaining until the threshold is crossed."""
        delta_temp = p30 - current
        if abs(delta_temp) < 0.05: return None # No significant movement
        
        # Calculate degrees per minute (30-minute window)
        rate_per_min = delta_temp / 30
        
        # Minutes = (Target - Current) / Rate
        if rate_per_min > 0: # Warming up
            mins = (self.THRESHOLD - current) / rate_per_min
        else: # Cooling down
            mins = (current - self.THRESHOLD) / abs(rate_per_min)
            
        return max(0, int(mins))

    def get_contextual_status(self, current, p30, p60):
        eta = self.calculate_eta(current, p30)
        
        # Scenario: Heat is rising
        if p30 > current and p30 >= self.THRESHOLD:
            time_str = f"in {eta} minutes" if eta and eta < 60 else "shortly"
            msg = f"Thermal energy is rising. I will engage the AC {time_str} to maintain your comfort."
            cmd = "YELLOW_BLINK"
            
        # Scenario: Cooling down
        elif p30 < current and current >= self.THRESHOLD:
            time_str = f"in {eta} minutes" if eta and eta < 60 else "soon"
            msg = f"The heat is starting to break. I'll be able to switch off the FAN {time_str} to save energy."
            cmd = "GREEN_ON" # Still on, but with a shutdown CTA

        else:
            msg = "Climate is stable. No manual action or automated changes required for the next hour."
            cmd = "RED_ON"

        return cmd, msg