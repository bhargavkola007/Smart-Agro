"""
Smart Agro - Sensor Simulator
Sends fake sensor data to Flask every 2 seconds.
Run this while app.py is running in another terminal.

Usage: python simulate.py
"""

import requests
import random
import time
import math

URL = "http://127.0.0.1:5000/api/sensor-data"

# Simulate slow natural drift using sine waves
tick = 0

def get_fake_data(tick):
    # Moisture: oscillates between 30–80%
    moisture = 55 + 25 * math.sin(tick * 0.08) + random.uniform(-3, 3)
    moisture = round(max(0, min(100, moisture)), 1)

    # pH: drifts between 5.5–8.5
    ph = 7.0 + 1.5 * math.sin(tick * 0.05 + 1) + random.uniform(-0.1, 0.1)
    ph = round(max(0, min(14, ph)), 2)

    # Turbidity: slower drift 5–70%
    turbidity = 35 + 30 * math.sin(tick * 0.03 + 2) + random.uniform(-2, 2)
    turbidity = round(max(0, min(100, turbidity)), 1)

    if   turbidity < 20: turb_status = "CLEAR"
    elif turbidity < 50: turb_status = "CLOUDY"
    else:                turb_status = "DIRTY"

    return {
        "moisture":    moisture,
        "ph":          ph,
        "turbidity":   turbidity,
        "turb_status": turb_status
    }

print("=== Smart Agro Simulator ===")
print(f"Sending data to: {URL}")
print("Press Ctrl+C to stop\n")

while True:
    data = get_fake_data(tick)
    try:
        r = requests.post(URL, json=data, timeout=3)
        status = "OK" if r.status_code == 200 else f"ERR {r.status_code}"
    except requests.exceptions.ConnectionError:
        status = "CANNOT CONNECT — is app.py running?"
    except Exception as e:
        status = str(e)

    print(f"[{tick:04d}] Moisture={data['moisture']}%  pH={data['ph']}  "
          f"Turbidity={data['turbidity']}% ({data['turb_status']})  → {status}")

    tick += 1
    time.sleep(2)
