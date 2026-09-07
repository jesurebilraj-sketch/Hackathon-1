# AI-Powered Learning Management System & Course Builder - Backend

Welcome to the backend service of the **AI-Powered Learning Management System & Course Builder**. This service provides REST APIs for course generation, lesson workflows, interactive AI tutoring, intelligent study planning, and learning analytics.

---

## Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL (SQLAlchemy ORM + Psycopg2)
- **Data Validation**: Pydantic v2
- **Document Processing**: PyMuPDF (*upcoming phase*)
- **Vector Search / RAG**: FAISS / Chroma (*upcoming phase*)
- **AI / LLM Orchestration**: Structured outputs via Pydantic (*upcoming phase*)

---

## Project Structure

```
backend/
├── main.py              # FastAPI application entrypoint & middleware
├── requirements.txt     # Python package dependencies
├── .env                 # Local environment configuration (do NOT commit)
├── .env.example         # Template for environment variables
├── api/                 # Modular REST API route handlers
│   ├── courses.py       # Course management endpoints
│   ├── lessons.py       # Lesson management endpoints
│   ├── quizzes.py       # Quiz endpoints (stubbed)
│   ├── tutor.py         # AI Tutor endpoints (stubbed)
│   ├── planner.py       # Study Planner endpoints (stubbed)
│   └── analytics.py     # Analytics endpoints (stubbed)
└── database/            # Database engine and ORM models
    ├── database.py      # SQLAlchemy connection, sessionmaker, & init_db
    └── models.py        # Core models (User, Course, Module, Lesson)
```

---

## Step-by-Step Setup Guide

### 1. Create the Virtual Environment

From the project root directory, create a Python 3.10+ virtual environment:

**Windows (PowerShell / Command Prompt):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
# Or in Command Prompt:
# .\venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 2. Install Dependencies

With the virtual environment activated, install all required packages:

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

---

### 3. Configure Environment Variables (`.env`)

Copy the `.env.example` template to `.env`:

**Windows PowerShell:**
```powershell
Copy-Item backend\.env.example backend\.env
```

**macOS / Linux:**
```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and configure your database connection:

```env
# Application Settings
APP_NAME="AI-Powered LMS & Course Builder"
APP_ENV=development
PORT=8000
HOST=0.0.0.0

# Allowed Frontend Origins for CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# PostgreSQL Database Connection URL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lms_db

# Local SQLite Fallback (if running without local PostgreSQL):
# DATABASE_URL=sqlite:///./lms.db
```

---

### 4. Start PostgreSQL

You can run PostgreSQL in any of the following ways:

#### Option A: Docker (Recommended for quick hackathon setup)
```bash
docker run --name lms-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=lms_db -p 5432:5432 -d postgres:16
```

#### Option B: Local PostgreSQL Service
1. Install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/).
2. Create the database:
   ```sql
   CREATE DATABASE lms_db;
   ```
3. Update `DATABASE_URL` in `backend/.env` with your username and password.

#### Option C: Cloud Database (Neon / Supabase)
1. Create a free PostgreSQL instance on [Neon.tech](https://neon.tech) or [Supabase](https://supabase.com).
2. Paste the connection string into `DATABASE_URL` in `backend/.env`.

#### Option D: Instant Local Testing (SQLite)
If PostgreSQL is not yet available, set in `backend/.env`:
```env
DATABASE_URL=sqlite:///./lms.db
```

---

### 5. Run the FastAPI Application

Navigate into the `backend` folder and launch the Uvicorn development server:

```powershell
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The application will start at:
- **Base URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

### 6. Test the Health Endpoint

#### Using cURL / PowerShell:
```powershell
# PowerShell:
Invoke-RestMethod -Uri "http://localhost:8000/health"

# cURL:
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok"
}
```

#### Database Health Check:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health/db"
```

**Expected Response:**
```json
{
  "status": "ok",
  "database": {
    "status": "connected",
    "database": "lms_db"
  }
}
```
