# 🐍 Raspberry Pi & KNN Setup Guide

This document explains how to set up and run the **Raspberry Pi data-collection and KNN classification system**.  
The Pi reads water-quality sensors through the MCP3008 ADC, performs local KNN analysis, and sends the readings + results to the **self-hosted Supabase** backend.

---

## 📘 Overview

### Responsibilities
- Read **analog sensors** (Temperature, pH, TDS) via **MCP3008**  
- Run a **KNN model** on the collected readings  
- Upload sensor + classification data to Supabase  
- Capture images (handled by `single.py`) and forward them to the CNN container

### Data Flow
```text
MCP3008 → sensor_reader.py → knn.py → Supabase (sensor_readings)
```

---

## Folder Structure
```bash
raspi/
├── sensor.py            # Reads sensor data through MCP3008
├── knn.py               # Classifies readings using KNN and pushes results
├── cam.py               # Captures images and sends to CNN container
├── model_knn.pkl        # (optional) serialized KNN model
```

---

## ⚙️ Hardware Requirements

| Component                        | Purpose                            |
| -------------------------------- | ---------------------------------- |
| Raspberry Pi (3B/4B recommended) | Main controller                    |
| MCP3008 ADC                      | Converts analog signals to digital |
| pH Sensor                        | Measures acidity                   |
| TDS Sensor                       | Measures dissolved solids          |
| DS18B20 or Analog Temp Sensor    | Temperature measurement            |
| USB Camera                       | Image capture                      |
| Jumper Wires + Breadboard        | Circuit connections                |

---

## Wiring Guide

| MCP3008 Pin           | Connects To    | Description       |
| --------------------- | -------------- | ----------------- |
| VDD → 3.3 V           | Pi 3.3 V Power | Chip power        |
| VREF → 3.3 V          | Pi 3.3 V       | Reference voltage |
| AGND → GND            | Pi Ground      | Analog ground     |
| DGND → GND            | Pi Ground      | Digital ground    |
| CLK → GPIO11 (SCLK)   | Clock          |                   |
| DOUT → GPIO9 (MISO)   | Data output    |                   |
| DIN → GPIO10 (MOSI)   | Data input     |                   |
| CS/SHDN → GPIO8 (CE0) | Chip select    |                   |

Then connect:

- CH0 → TDS sensor

- CH1 → pH sensor

```text
⚠️ Enable SPI on the Pi:
sudo raspi-config → Interfacing Options → SPI → Enable
```

---

## Software Setup

Install Dependencies
```bash
sudo apt update
sudo apt install python3-pip git python3-spidev -y
pip install -r requirements.txt
```
Example requirements.txt
```nginx
requests
spidev
adafruit-circuitpython-mcp3xxx
numpy
scikit-learn
supabase
```

---

## Supabase Configuration
In each script (knn.py, sensor_reader.py) set:

```python 
SUPABASE_URL = "http://<host-machine-ip>:3000"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.DEMOANON.KEY"
SUPABASE_TABLE = "sensor_readings"
```

```text
Replace <host-machine-ip> with the local IP of the computer running Supabase.
(You can find it using hostname -I on the host machine.)
```

---

## Pipeline Execution

### Step 1 – Sensor Reading

Run:
```bash
python3 sensor.py
```
It continuously prints and returns JSON-formatted readings:
```json
{"temp": 25.6, "ph": 7.1, "tds": 420}
```
These values are passed to knn.py.

### Step 2 – KNN Classification

Run:
```bash
python3 knn.py
```
Typical workflow inside knn.py:
```python
from sklearn.neighbors import KNeighborsClassifier
import joblib, json, requests

# Load pre-trained model
model = joblib.load("model_knn.pkl")

# Example incoming data
data = {"temp":25.6, "ph":7.1, "tds":420}
X = [[data["temp"], data["ph"], data["tds"]]]
label = model.predict(X)[0]
conf = max(model.predict_proba(X)[0])

payload = {
  "raspi_id": "raspi-01",
  "readings": data,
  "classification": label,
  "confidence": round(float(conf), 3)
}

requests.post(f"{SUPABASE_URL}/{SUPABASE_TABLE}",
              headers={"Authorization": f"Bearer {SUPABASE_KEY}"},
              json=payload)
```

### Step 3 – Image Capture (for CNN)

Run:
```bash
python3 cam.py
```
Snippet:
```python 
import cv2, requests

url = "http://<host-ip>:8080/predict"
cam = cv2.VideoCapture(0)
ret, frame = cam.read()
cv2.imwrite("capture.jpg", frame)
with open("capture.jpg", "rb") as f:
    res = requests.post(url, files={"file": f})
print(res.json())
```
The response contains CNN prediction results which are then sent to Supabase.

---

## Full Automation (Optional)

To auto-start scripts on boot:
```bash
sudo nano /etc/rc.local
# Add before 'exit 0':
python3 /home/pi/raspi/sensor_reader.py &
python3 /home/pi/raspi/knn.py &
python3 /home/pi/raspi/single.py &
```

---

## Testing Data Flow

1. Start Supabase (docker compose up -d)
2. Run sensor_reader.py → knn.py
3. Open Supabase Studio → sensor_readings
4. Verify live rows inserted with timestamp, values, and classification.

---

## KNN Model Training (Optional)
You can train a new KNN model locally:
```python 
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
import joblib

df = pd.read_csv("training_data.csv")
X = df[["temp", "ph", "tds"]]
y = df["label"]

model = KNeighborsClassifier(n_neighbors=3)
model.fit(X, y)
joblib.dump(model, "model_knn.pkl")
```
Copy model_knn.pkl to the raspi/ folder.

---

## Troubleshooting

| Problem                     | Cause                        | Fix                                                                   |
| --------------------------- | ---------------------------- | --------------------------------------------------------------------- |
| MCP3008 reads 0 always      | SPI disabled or wrong wiring | Enable SPI & verify GPIOs                                             |
| Supabase refuses connection | Wrong IP or API port         | Ensure host is reachable & port 3000 open                             |
| KNN script crashes          | Missing `model_knn.pkl`      | Train or provide the model file                                       |
| Data not in DB              | Invalid API key or URL       | Check `SUPABASE_URL` and `SUPABASE_KEY`                               |
| Camera error                | No camera detected           | Check `/dev/video0` exists or try `sudo raspi-config` → Enable Camera |
