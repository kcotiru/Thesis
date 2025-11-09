# CNN Container Setup Guide

This guide explains how to build, configure, and run the **CNN-based image prediction service** used in this project.  
It uses **FastAPI** + **PyTorch** and runs inside a **Docker container** for reproducibility and offline capability.

---

## Overview

The CNN container is responsible for:
- Receiving captured images from the Raspberry Pi (`single.py`)
- Running inference using a trained PyTorch model (e.g., `resnet.pth`)
- Sending prediction results to the self-hosted **Supabase** backend

This container is designed to:
- Work **offline** in local research environments  
- Integrate easily with the rest of the system via REST API  
- Be easily **retrained** or replaced by future developers

---

## Folder Structure

Expected structure inside `/app`:

```text
├── app/
│ └── server.py # FastAPI server that handles image inference
├── model/
│ └── rcnn.pth # Trained PyTorch model (replaceable)
├── Dockerfile # Docker build configuration
```


---

## ⚙️ Step 1. Verify Prerequisites

Make sure you have the following installed:

| Tool | Version | Purpose |
|------|----------|----------|
| Docker | ≥ 24.x | Runs the containerized service |
| Python | ≥ 3.10 | (Optional) For local testing before Docker |
| Git | Latest | To clone and manage code |

If running on a Raspberry Pi or local machine, ensure you can connect to your self-hosted Supabase backend.

---

## Step 2. Review the Dockerfile

Here’s the Dockerfile included in this project:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY ./model /model
COPY ./app /app

RUN pip install --no-cache-dir \
    torch==2.8.0+cpu torchvision==0.23.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    Pillow \
    psycopg2-binary

EXPOSE 8080
ENV MODEL_PATH=/model/resnet.pth
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
```

Key Notes:

Uses CPU-only PyTorch (for lightweight deployment)

Exposes port 8080

The model file is read from /model/resnet.pth

Starts the FastAPI app defined in server.py

---

## Step 3. Build the Container

Run this from the project root or /inference directory:
```bash
docker build -t cnn-service .
```
This command:

Downloads dependencies

Copies your app and model files

Packages everything into a single container image named cnn-service

---

## Step 4. Run the Container

Once built, start the container:
```bash
docker run -d -p 8080:8080 cnn-service
```

Confirm it’s running:
```bash
docker ps
```

You should see:
```bash
CONTAINER ID   IMAGE          COMMAND                  PORTS                    NAMES
<id>           cnn-service    "uvicorn server:app…"    0.0.0.0:8080->8080/tcp   cnn-service
```

---

## Step 5. Test the API

The FastAPI service runs locally on:
```bash
http://localhost:8080/predict
```

Example: Send a test image
```bash
curl -X POST "http://localhost:8080/predict" \
  -F "file=@sample_image.jpg"
```
Expected response:
```json
{
  "label": "normal",
  "confidence": 0.945,
  "model_version": "resnet-v1.0",
  "timestamp": "2025-10-14T12:00:45Z"
}
```

---

## Integration with Supabase
The container automatically sends prediction results to Supabase using Python’s psycopg2 or Supabase REST API.

You can configure the connection by editing environment variables or hardcoding the Supabase credentials in server.py.

Example configuration inside server.py:
```python
SUPABASE_URL = "http://localhost:3000"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.DEMOANON.KEY"
SUPABASE_TABLE = "image_predictions"
```
Whenever an image is processed, results are inserted into this table:

| Column | Type | Example |
|------|----------|----------|
| raspi_id | TEXT | "raspi-01" |
| timestamp |TIMESTAMP | "2025-10-14T12:00:45Z" |
| label | TEXT | "normal" |
| confidence | FLOAT | 0.945 |
| image_path | TEXT | "/images/img_20251014_120045.jpg" |
| model_version | TEXT | "rcnn-v1.0" |

---

## Integration with Raspberry Pi
The Raspberry Pi script single.py captures images using a webcam and sends them to the CNN container:
```python
url = "http://<host-machine-ip>:8080/predict"
files = {"file": open("capture.jpg", "rb")}
response = requests.post(url, files=files)
print(response.json())
```
```text
Replace <host-machine-ip> with the IP address of the computer running the CNN container.
```
---

## Stop and Manage the Container

Stop the CNN container:
```bash
docker stop cnn-service
```
Restart it:
```bash
docker start cnn-service
```
View live logs:
```bash
docker logs -f cnn-service
```
Remove the container:
```bash
docker rm -f cnn-service
```
---

## Model Replacement or Retraining

You can update the model anytime without rebuilding the entire container.
1. Replace the file at:
```bash
model/resnet.pth
```
2. Rebuild the image:
```bash
docker build -t cnn-service .
```
3. Restart the container.

If you wish to use a different model architecture, ensure server.py loads it correctly.

Example snippet:
```python
model = torch.load(os.getenv("MODEL_PATH"), map_location="cpu")
model.eval()
```
---

## Troubleshooting

| Issue | Possible Cause | Fix |
|------|----------|----------|
| torch import errors | Version mismatch | Rebuild the container |
| Port 8080 in use | Another service using it | Run on a different port (-p 8090:8080) |
| Supabase connection refused | Supabase not running | Start Supabase via docker compose up -d |
| Slow predictions | Using CPU-only PyTorch | Try use CUDA supported PyTorch  |