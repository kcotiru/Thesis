# Supabase Setup Guide

This guide explains how to **self-host Supabase** using Docker and configure it as the central database and API for your Raspberry Pi + CNN system.  
It will allow you (and future researchers) to run the full stack **offline**, without relying on the Supabase Cloud service.

---

## Overview

Supabase provides:
- **PostgreSQL database** for storing sensor readings and model outputs  
- **REST API (PostgREST)** for communication with your Python scripts  
- **Supabase Studio** web interface for managing data visually  

In this project, Supabase stores:
- KNN results from the Raspberry Pi (sensor readings)  
- CNN results from the image inference container  

---

## Folder Structure

You should have a folder named `supabase/` inside your repository:

```text
supabase/
├── docker-compose.yml # Defines Supabase services
├── .env # Environment configuration
├── migrations/ # SQL schema setup files
│ └── 2025-10-14-init.sql
└── seed.sql # Optional test data
```

---

## ⚙️ Prerequisites

| Requirement | Version | Description |
|--------------|----------|-------------|
| Docker | ≥ 24.x | Runs Supabase and PostgreSQL |
| Docker Compose | ≥ 2.x | Manages multi-container services |
| Git | Latest | To clone the repository |

Optional (for CLI access):  
`psql` PostgreSQL client

---

## Configure Environment Variables

Create or verify the `.env` file inside `supabase/`.

Example contents:

```bash
POSTGRES_PASSWORD=postgres
ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.DEMOANON.KEY
SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.DEMOSERVICE.KEY
JWT_SECRET=demosecret123
SUPABASE_URL=http://localhost:3000
SUPABASE_DB_URL=postgres://postgres:postgres@localhost:5432/postgres
```
⚠️ These demo credentials are public-safe — meant for research or local testing only.

---

## Start Supabase with Docker Compose

From the supabase/ directory, run:
```bash
docker compose up -d
```
This launches three main services:

- Postgres → Database (port 5432)

- PostgREST → REST API (port 3000)

- Supabase Studio → Web Dashboard (port 8080)

---

## Access the Supabase Dashboard

Open your browser to:
```arduino
http://localhost:8080
```
You can now:

- Browse database tables

- Manually insert or edit data

- Verify that incoming KNN/CNN data appears in real time

---

## Verify Containers Are Running

Check container status:
```bash
docker ps
```
Expected names:
```bash
supabase-db
supabase-postgrest
supabase-studio
```
If they aren’t listed, review logs:
```bash
docker compose logs -f
```

---

## Database Schema Overview

sensor_readings (KNN Results)

| Column | Type | Description |
|------|----------|----------|
| id | UUID | Unique identifier |
| raspi_id | TEXT | Device ID (e.g., “raspi-01”) |
| timestamp | TIMESTAMPS | Reading time |
| readings | JSONB | Sensor data (temp, pH, TDS) |
| classification | TEXT | KNN result (e.g., “normal”, “abnormal”) |
| confidence | NUMERIC(5,3) | Confidence score (0-1) |
| model_version | TEXT | KNN model version |
| analyzed_at | TIMESTAMPS | Time processed |

image_predictions (CNN Results)

| Column | Type | Description |
|------|----------|----------|
| id | UUID | Unique identifier |
| raspi_id | TEXT | Device ID (e.g., “raspi-01”) |
| timestamp | TIMESTAMPS | Capture time |
| image_path | TEXT | Saved image path |
| label | TEXT | Predicted label |
| confidence | NUMERIC(5,3) | Confidence score (0-1) |
| raw_output | JSONB | Full prediction data |
| model_version | TEXT | CNN model version |
| analyzed_at | TIMESTAMPS | Inference timestamp |

---

## Test the API
Supabase exposes an HTTP REST API on port 3000.

- Insert sample data
```bash
curl -X POST "http://localhost:3000/sensor_readings" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.DEMOANON.KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "raspi_id": "raspi-01",
        "readings": {"temp": 25.8, "ph": 7.0, "tds": 410},
        "classification": "normal",
        "confidence": 0.94
      }'
```
- Query stored data
```bash
curl "http://localhost:3000/sensor_readings?raspi_id=eq.raspi-01"
```

---

## Backup & Restore

Backup the database
```bash
docker exec supabase-db pg_dump -U postgres --no-owner postgres > backup.sql
```
Restore a backup
```bash
docker exec -i supabase-db psql -U postgres postgres < backup.sql
```

---

## Stop or Remove Containers
Stop all Supabase services:
```bash
docker compose down
```
Stop and delete all data volumes (fresh reset):
```bash
docker compose down -v
```

---

## Integration with the System

- From Raspberry Pi

sensor_reader.py and knn.py send JSON data directly to Supabase’s REST API endpoint
(http://<host-ip>:3000/sensor_readings).

- From CNN Container

server.py (FastAPI app) connects to Supabase (image_predictions table)
to upload image inference results and confidence scores.

---

## Troubleshooting

| Problem | Possible Cause | Fix |
|------|----------|----------|
| port 8080 already in use | Another service is running | Edit docker-compose.yml to change ports |
| Supabase Studio not loading | loading Container crash or build failed | Run docker compose logs -f |
| Data not saving | Wrong keys or URL | Check .env and ensure Raspberry Pi uses correct SUPABASE_URL |
| API 404 errors | Wrong table or endpoint | Confirm table name matches |