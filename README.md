# AI Ads Generation Platform

Production‑grade, end‑to‑end system for generating **commercial video advertisements** using Google Gemini (Nano Banana & VEO 3.1), ElevenLabs TTS, and AWS infrastructure.

This platform automatically generates:

* Consistent **AI characters** (face + outfit locked)
* Professional **scene images**
* **VEO 3.1 videos** from still images
* Natural **voiceovers**
* A **single final merged ad video** ready for delivery

Designed for **real advertising workflows**, not demos.

---

##  Key Features

*  **Character & Outfit Locking**
  Same person, same outfit, across all scenes (image‑locked, not text‑locked)

*  **Nano Banana Image Generation (Gemini 2.5 Flash Image)**
  High‑quality, photorealistic images optimized for video animation

*  **VEO 3.1 Video Generation**
  Converts static images into stable, cinematic videos with safe motion presets

*  **ElevenLabs Voiceovers**
  Scene‑wise narration with automatic duration fitting

*  **Automatic Video Merging**
  FFmpeg pipeline with fades, audio sync, and cleanup

*  **AWS S3 Storage**
  Images, videos, and final ads stored and served from S3

*  **VEO‑Safe Prompt Engineering**
  Avoids blur, bokeh, unstable framing, and aspect‑ratio issues

*  **Supabase / PostgreSQL Backend**
  Campaigns and scenes persisted via SQLAlchemy

---

##  Architecture Overview

The system is designed as a **modular, production-grade pipeline** where each stage is isolated, testable, and replaceable.

### High-Level Flow

```
Client / UI
   │
   ▼
FastAPI Backend (Gunicorn + systemd)
   │
   ├── Campaign API (FastAPI Routers)
   ├── Database Layer (SQLAlchemy + Supabase/PostgreSQL)
   ├── Image Generation
   │     └─ Gemini 2.5 Flash Image (Nano Banana)
   │         └─ Character + Scene Images
   ├── Video Generation
   │     └─ VEO 3.1 (Image → Video)
   ├── Audio Generation
   │     └─ ElevenLabs TTS (Scene-wise)
   ├── Media Processing
   │     └─ FFmpeg (audio fit, fades, merge)
   └── Storage
         └─ AWS S3 (images, videos, final ads)
```

### Key Architectural Decisions

* **Image-locked identity** (face + outfit) for consistency
* **Scene-image-only VEO input** (VEO 3.1 safe mode)
* **No reliance on unstable aspect-ratio enforcement**
* **Retry + cleanup logic** for long-running media tasks
* **Stateless API** with persistent DB + object storage


---


##  Environment Variables

Create a `.env` file:

```env
# Gemini
GEMINI_API_KEY=your_gemini_key

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
S3_CAMPAIGN_BUCKET=Your_Bucket_Name

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Server
HOST=0.0.0.0
PORT=8001
```

---

##  Project Setup & Installation

### 1️ Clone the Repository

```bash
git clone <your-repo-url>
cd AI-Ads_Generation
```

---

### 2️ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows
```

---

### 3️ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️ Environment Variables

Create a `.env` file in the project root:

```env
# Gemini (Nano Banana + VEO)
GEMINI_API_KEY=your_gemini_api_key

# AWS S3
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
S3_CAMPAIGN_BUCKET=ai-images-2

# Database (Supabase / PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Server
HOST=0.0.0.0
PORT=8001
```

---

##  Running the Backend

### Development Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Production Mode (Recommended)

* Gunicorn
* systemd service
* Nginx reverse proxy

Example:

```bash
gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

---

##  API Documentation (Swagger / OpenAPI)

FastAPI automatically exposes interactive API docs.

### Swagger UI

```
http://<server-ip>:8001/docs
```

### ReDoc

```
http://<server-ip>:8001/redoc
```

### OpenAPI JSON

```
http://<server-ip>:8001/openapi.json
```

>  Swagger is tested and stable on **port 8001**

---

##  Health Check

```http
GET /health
```

Response:

```json
{ "status": "healthy" }
```

---

##  Deployment

##  Health Check

```http
GET /health
```

Response:

```json
{ "status": "healthy" }
```

---


##  License

Private / Proprietary (update as needed)

---

**Built for real ads, real clients, and real delivery.**

