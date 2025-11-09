import os
import time
import uuid
import json
import requests
from datetime import datetime

try:
    import spidev
except ImportError:
    raise RuntimeError("spidev not found. Install via: sudo apt install python3-spidev")

# === CONFIG ===
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:8000")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "example_key")
TABLE = os.getenv("SUPABASE_TABLE", "sensor_readings")
RASPI_ID = os.getenv("RASPI_ID", "raspi-01")
READ_INTERVAL = float(os.getenv("READ_INTERVAL", "5"))

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

INSERT_URL = f"{SUPABASE_URL}/rest/v1/{TABLE}"

# === SPI / MCP3008 SETUP ===
spi = spidev.SpiDev()
spi.open(0, 0) 
spi.max_speed_hz = 1350000  

PH_CHANNEL = int(os.getenv("PH_CHANNEL", "0"))
TDS_CHANNEL = int(os.getenv("TDS_CHANNEL", "1"))

def read_channel(channel: int) -> int:
    if not 0 <= channel <= 7:
        raise ValueError("MCP3008 channel must be 0–7")
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    data = ((adc[1] & 3) << 8) | adc[2]
    return data

def convert_to_voltage(raw_value: int, vref: float = 3.3) -> float:
    return (raw_value / 1023.0) * vref

def estimate_ph(voltage: float) -> float:
    ph = 7 + ((2.5 - voltage) / 0.18)  # Adjust slope/offset for your sensor
    return round(ph, 2)

def estimate_tds(voltage: float, temp_c: float = 25.0) -> float:
    ec = (133.42 * voltage**3 - 255.86 * voltage**2 + 857.39 * voltage) * 0.5
    ec_comp = ec / (1 + 0.02 * (temp_c - 25.0))
    tds = ec_comp * 0.67  # Convert EC to TDS ppm
    return round(tds, 2)

def get_temperature() -> float:
    try:
        import random
        return round(25 + random.uniform(-1.5, 1.5), 2)
    except Exception:
        return 25.0

def read_sensors():
    ph_raw = read_channel(PH_CHANNEL)
    tds_raw = read_channel(TDS_CHANNEL)
    ph_voltage = convert_to_voltage(ph_raw)
    tds_voltage = convert_to_voltage(tds_raw)
    temp_c = get_temperature()
    ph_val = estimate_ph(ph_voltage)
    tds_val = estimate_tds(tds_voltage, temp_c)

    readings = {
        "temp": temp_c,
        "ph": ph_val,
        "tds": tds_val,
        "ph_voltage": round(ph_voltage, 3),
        "tds_voltage": round(tds_voltage, 3),
    }
    return readings

def post_reading(data):
    try:
        res = requests.post(INSERT_URL, headers=HEADERS, json=data, timeout=10)
        if res.status_code not in (200, 201, 204):
            print("[WARN] Insert failed:", res.status_code, res.text)
        else:
            print(f"[OK] Sent reading: {data['readings']}")
    except Exception as e:
        print("[ERROR] Network issue:", e)

def main():
    print("Sensor reader (MCP3008) started.")
    while True:
        readings = read_sensors()
        payload = {
            "id": str(uuid.uuid4()),
            "raspi_id": RASPI_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "readings": readings
        }
        post_reading(payload)
        time.sleep(READ_INTERVAL)

if __name__ == "__main__":
    main()
