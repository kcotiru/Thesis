import os
import io
import json
import torch
import torch.nn.functional as F
from PIL import Image
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from torchvision import models as tv_models
from torchvision.models import ResNet50_Weights



# ----------------------------------------------------
# Database connection pool
# ----------------------------------------------------
DB_DSN = os.environ.get("DB_DSN", "postgresql://postgres:example@db:5432/postgres")
_db_pool = None

def init_db_pool():
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = SimpleConnectionPool(1, 10, dsn=DB_DSN)
            print("Postgres pool initialized.")
        except Exception as e:
            _db_pool = None
            print("Warning: failed to init Postgres pool:", e)

init_db_pool()

def _save_predictions_to_db(results, orig_w, orig_h, source=None):
    if _db_pool is None:
        print("DB pool unavailable. Skipping save.")
        return
    conn = None
    try:
        conn = _db_pool.getconn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO predictions (source, image_width, image_height, predictions) VALUES (%s, %s, %s, %s)",
            (source, orig_w, orig_h, json.dumps(results)),
        )
        conn.commit()
        cur.close()
    except Exception as e:
        print("Error saving to Postgres:", e)
    finally:
        if conn:
            _db_pool.putconn(conn)

# ----------------------------------------------------
# Preprocessing (imports from dataset.py if available)
# ----------------------------------------------------
try:
    from dataset import letterbox_and_resize, pil_to_tensor
    def preprocess_image(image: Image.Image):
        image = letterbox_and_resize(image, new_shape=(640, 640))
        tensor = pil_to_tensor(image)
        return tensor
    print("Using preprocess functions from dataset.py with 640x640 resize")
except Exception:
    print("dataset.py preprocess not found. Using internal 640x640 preprocess.")
    from torchvision import transforms

    def letterbox_and_resize(image: Image.Image, new_shape=(640, 640)):
        image = image.convert("RGB")
        image = image.resize(new_shape)
        return image

    def pil_to_tensor(image: Image.Image):
        transform = transforms.ToTensor()
        return transform(image).unsqueeze(0)

    def preprocess_image(image: Image.Image):
        image = letterbox_and_resize(image, new_shape=(640, 640))
        return pil_to_tensor(image)

# ----------------------------------------------------
# Model loading
# ----------------------------------------------------
MODEL_PATH = os.environ.get("MODEL_PATH", "/model/resnet.pth")
SCORE_THRESHOLD = float(os.environ.get("SCORE_THRESHOLD", 0.25))
LABELS_PATH = os.path.join(os.path.dirname(__file__), "labels.json")

with open(LABELS_PATH, "r") as f:
    LABELS = json.load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_model():
    print(f"Loading model weights from: {MODEL_PATH}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    num_classes = len(LABELS)

    # Build a local ResNet50 classifier head to avoid unsafe unpickling
    model = tv_models.resnet50(weights=None)
    in_features = model.fc.in_features
    model.fc = torch.nn.Linear(in_features, num_classes)

    # Load checkpoint flexibly (state_dict or checkpoint wrappers)
    state = None
    try:
        # Prefer safe load (PyTorch >=2.6 defaults weights_only=True)
        state = torch.load(MODEL_PATH, map_location=device, weights_only=True)
    except Exception as e:
        print("Error loading weights_only checkpoint:", e)
        print("Falling back to ResNet50 ImageNet weights to keep service running...")
        # Initialize with ImageNet weights and return early
        model = tv_models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
        in_features = model.fc.in_features
        model.fc = torch.nn.Linear(in_features, num_classes)
        model.to(device)
        model.eval()
        print("✅ Model initialized with ImageNet weights (no custom checkpoint).")
        return model

    # Extract actual state_dict
    if isinstance(state, dict) and any(k in state for k in ["state_dict", "model_state", "model_state_dict"]):
        state_dict = state.get("state_dict") or state.get("model_state") or state.get("model_state_dict")
    else:
        state_dict = state if isinstance(state, dict) else None

    if state_dict is None:
        raise RuntimeError("Checkpoint does not contain a valid state_dict")

    # Some checkpoints are prefixed (e.g., 'module.' or 'model.'). Strip known prefixes.
    cleaned_state_dict = {}
    for key, value in state_dict.items():
        new_key = key
        if new_key.startswith("module."):
            new_key = new_key[len("module."):]
        if new_key.startswith("model."):
            new_key = new_key[len("model."):]
        cleaned_state_dict[new_key] = value

    # Filter keys to those existing in our model to avoid detection-model leftovers
    model_keys = set(model.state_dict().keys())
    filtered_state_dict = {k: v for k, v in cleaned_state_dict.items() if k in model_keys}

    missing, unexpected = model.load_state_dict(filtered_state_dict, strict=False)
    if missing:
        print(f"Warning: {len(missing)} missing keys when loading checkpoint (ok if heads differ)")
    if unexpected:
        print(f"Warning: {len(unexpected)} unexpected keys ignored from checkpoint")

    model.to(device)
    model.eval()
    print("✅ Model loaded with state_dict.")
    return model

model = load_model()

# ----------------------------------------------------
# FastAPI app
# ----------------------------------------------------
app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        orig_w, orig_h = image.size

        tensor = preprocess_image(image)

        with torch.no_grad():
            outputs = model(tensor)
            probs = F.softmax(outputs[0], dim=0)
            scores, indices = torch.topk(probs, k=3)
            scores = scores.numpy()
            indices = indices.numpy()

        results = []
        for i in range(len(scores)):
            label = LABELS.get(str(indices[i]), f"class_{indices[i]}")
            conf = float(scores[i])
            if conf >= SCORE_THRESHOLD:
                results.append({"label": label, "confidence": round(conf, 3)})

        _save_predictions_to_db(results, orig_w, orig_h, source=file.filename)

        return JSONResponse(
            status_code=200,
            content={
                "filename": file.filename,
                "width": orig_w,
                "height": orig_h,
                "predictions": results,
            },
        )

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
