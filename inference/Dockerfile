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
