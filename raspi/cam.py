import os
import cv2
import sys
import time
import json
import requests
from datetime import datetime

# --- CONFIGURATION ---
PREDICTOR_URL = os.getenv("PREDICTOR_URL", "http://localhost:8080/predict")
RASPI_ID = os.getenv("RASPI_ID", "raspi-unknown")
IMAGE_PATH = os.getenv("IMAGE_PATH", "./capture.jpg")
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
TIMEOUT = int(os.getenv("TIMEOUT", "30"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PREDICTION_TABLE = os.getenv("PREDICTION_TABLE", "predictions")

HEADERS_SUPA = None
if SUPABASE_URL and SUPABASE_KEY:
    HEADERS_SUPA = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    SUPA_INSERT_URL = f"{SUPABASE_URL}/rest/v1/{PREDICTION_TABLE}"
else:
    SUPA_INSERT_URL = None


# --- FUNCTIONS ---
def capture_with_webcam(path: str):
    """Capture an image from a USB webcam using OpenCV."""
    print("[INFO] Capturing image from webcam...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(f"Webcam not accessible at index {CAMERA_INDEX}")

    # Allow camera to adjust lighting
    time.sleep(0.5)

    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("Failed to capture image from webcam")

    cv2.imwrite(path, frame)
    print(f"[INFO] Image captured and saved to {path}")
    return path


def post_image_to_predictor(path: str):
    """Send image to the FastAPI /predict endpoint."""
    files = {"file": (os.path.basename(path), open(path, "rb"), "image/jpeg")}
    try:
        response = requests.post(PREDICTOR_URL, files=files, timeout=TIMEOUT)
        return response
    except Exception as e:
        print("[ERROR] Failed to send image to predictor:", e)
        return None


def save_prediction_to_supabase(pred_json):
    """Save prediction result to Supabase via REST API."""
    if SUPA_INSERT_URL is None:
        return False

    payload = {
        "raspi_id": RASPI_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "prediction": pred_json,
    }

    try:
        response = requests.post(SUPA_INSERT_URL, headers=HEADERS_SUPA, json=payload, timeout=10)
        if response.status_code in (200, 201):
            print("[INFO] Prediction saved to Supabase.")
            return True
        else:
            print("[WARN] Supabase insert failed:", response.status_code, response.text)
            return False
    except Exception as e:
        print("[ERROR] Supabase network error:", e)
        return False


def main():
    print("=== Webcam Capture and Prediction ===")
    try:
        path = capture_with_webcam(IMAGE_PATH)
    except Exception as e:
        print("[ERROR] Image capture failed:", e)
        sys.exit(1)

    response = post_image_to_predictor(path)
    if response is None:
        sys.exit(1)

    print("[INFO] Predictor response status:", response.status_code)
    try:
        result_json = response.json()
    except Exception:
        print("[ERROR] Non-JSON response from predictor:", response.text)
        sys.exit(1)

    print("[INFO] Predictor result:")
    print(json.dumps(result_json, indent=2))

    if SUPA_INSERT_URL:
        save_prediction_to_supabase({"image_path": path, "result": result_json})


if __name__ == "__main__":
    main()
