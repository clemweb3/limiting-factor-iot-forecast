import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("PROACTIVE_API_KEY")
URL = "http://localhost:8000/telemetry"
HEADERS = {"x-api-key": API_KEY}

# We will simulate a rising temperature to trigger the Proactive CTA
current_temp = 27.0 

print("Starting ESP32 Simulation (Rising Temp Trend)...")

for i in range(10):
    current_temp += 0.5 # Simulate things getting hotter
    payload = {"temp": current_temp, "hum": 65.0}
    
    try:
        response = requests.post(URL, params=payload, headers=HEADERS)
        data = response.json()
        print(f"Read: {current_temp}°C | AI Says: {data['cta']}")
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(3) # Send every 3 seconds for the demo