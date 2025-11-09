# 🧠 Smart Aquatic Monitoring System  
### Real-Time Water Quality & Fish Behavior Analysis Using Raspberry Pi, KNN, CNN, and Self-Hosted Supabase

---

## 📘 Overview

This project implements a **hybrid monitoring system** that integrates:
- 🌡️ **Sensor-based KNN classification** for detecting water quality anomalies, and  
- 🎥 **CNN-based image analysis** for observing fish behavior,  
all coordinated through a **self-hosted Supabase** backend running on Docker.

The system is designed to be **fully reproducible and open-source**, serving as a **research legacy** for future students, developers, or thesis teams to build upon.  

---

## 🧱 System Architecture

```text
                                +---------------------------------------------------------+
                                |                    Raspberry Pi (Edge)                  |
                                |---------------------------------------------------------|
                                | • Reads analog sensors (Temp, pH, TDS) via MCP3008      |
                                | • Runs KNN classifier on readings                       |
                                | • Captures images via webcam                            |
                                | • Sends sensor data + images to Docker services         |
                                +---------------------------------------------------------+
                                                           |
                                                           v
                                +---------------------------------------------------------+
                                |                CNN Docker Container                     |
                                |---------------------------------------------------------|
                                | • Receives images from Raspberry Pi                     |
                                | • Runs CNN model (PyTorch + FastAPI)                    |
                                | • Sends predictions to Supabase                         |
                                +---------------------------------------------------------+
                                                           |
                                                           v
                                +---------------------------------------------------------+
                                |                   Supabase (Self-Hosted)                |
                                |---------------------------------------------------------|
                                | • PostgreSQL database for storage                       |
                                | • REST API (PostgREST) for data exchange                |
                                | • Supabase Studio for data visualization                |
                                +---------------------------------------------------------+
```
# ⚙️ System Setup Guide

This section explains how to **set up and run the entire system** — from the self-hosted Supabase backend, to the Raspberry Pi scripts, and the CNN Docker container.  
Everything runs **locally** and is designed for **reproducible research** or thesis continuation.

---

## 🧩 1️⃣ Requirements

Before you begin, ensure the following are installed:

| Component | Version | Purpose |
|------------|----------|----------|
| **Docker** | ≥ 24.x | Runs the Supabase and CNN containers |
| **Docker Compose** | ≥ 2.x | Manages multiple containers |
| **Python** | ≥ 3.10 | Runs Raspberry Pi scripts |
| **Pip** | Latest | For Python dependency management |
| **Git** | Latest | For cloning the repository |

Optional hardware:
- Raspberry Pi (tested on 4B)
- MCP3008 ADC chip for analog sensors
- pH, TDS, and temperature sensors
- USB webcam for image capture

---

## 🧱 2️⃣ Clone the Repository

Clone the full project, which includes:
- `supabase/` → database backend  
- `app/` → CNN service  
- `raspi/` → sensor and KNN scripts

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```
