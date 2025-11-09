import os
import time
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
import joblib

# === CONFIG ===
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:8000")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "example_key")
TABLE = os.getenv("SUPABASE_TABLE", "sensor_readings")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "5"))
K = int(os.getenv("K", "3"))
MODEL_FILE = os.getenv("MODEL_FILE", "./knn_model.joblib")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

SELECT_URL = f"{SUPABASE_URL}/rest/v1/{TABLE}?select=*&classification=is.null&order=timestamp.asc"
UPDATE_URL = f"{SUPABASE_URL}/rest/v1/{TABLE}"

# === TRAINING OR LOADING ===
def build_or_load_model():
    if os.path.exists(MODEL_FILE):
        print("Loading existing KNN model...")
        obj = joblib.load(MODEL_FILE)
        return obj["model"], obj["scaler"], obj["features"]

    print("Training simple fallback model...")
    df = pd.DataFrame({
        "temp": [22, 25, 28, 30],
        "ph": [6.8, 7.0, 7.4, 7.8],
        "tds": [300, 350, 400, 450],
        "label": ["low", "normal", "normal", "high"]
    })

    features = ["temp", "ph", "tds"]
    X = df[features].values
    y = df["label"].values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    model = KNeighborsClassifier(n_neighbors=K)
    model.fit(Xs, y)
    joblib.dump({"model": model, "scaler": scaler, "features": features}, MODEL_FILE)
    print("Model trained and saved.")
    return model, scaler, features

# === FETCH & UPDATE ===
def fetch_unclassified():
    try:
        r = requests.get(SELECT_URL, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print("Fetch failed:", r.status_code, r.text)
            return []
    except Exception as e:
        print("Error fetching data:", e)
        return []

def classify_row(row, model, scaler, features):
    readings = row.get("readings") or {}
    values = [readings.get(f, 0.0) for f in features]
    X = np.array(values).reshape(1, -1)
    Xs = scaler.transform(X)
    label = model.predict(Xs)[0]
    try:
        conf = model.predict_proba(Xs).max().item()
    except Exception:
        conf = None
    return label, conf

def update_row(row_id, classification, confidence):
    patch_url = f"{UPDATE_URL}?id=eq.{row_id}"
    payload = {
        "classification": classification,
        "confidence": confidence,
        "analyzed_at": datetime.utcnow().isoformat()
    }
    try:
        res = requests.patch(patch_url, headers=HEADERS, json=payload, timeout=10)
        if res.status_code in (200, 204):
            print(f"[OK] Updated {row_id} → {classification} ({confidence:.2f})")
        else:
            print("Update failed:", res.status_code, res.text)
    except Exception as e:
        print("Network error updating:", e)

# === MAIN LOOP ===
def main():
    model, scaler, features = build_or_load_model()
    print("Monitoring Supabase for new sensor readings...")
    while True:
        items = fetch_unclassified()
        if items:
            print(f"Found {len(items)} new readings.")
            for item in items:
                label, conf = classify_row(item, model, scaler, features)
                update_row(item["id"], label, conf or 0.0)
        else:
            print("No new readings.")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
