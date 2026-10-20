# SQL Query Optimizer & Performance Intelligence Platform

A high-performance query analysis and execution plan intelligence engine built to diagnose bottlenecks, examine PostgreSQL execution plans, suggest indexes, and perform safe SQL rewrites.

## Tech Stack
- **Backend:** FastAPI, Python 3.14 / 3.11+
- **Database:** PostgreSQL (with SQLAlchemy 2.0 & Psycopg3)
- **Migrations:** Alembic (Phase 1.2+)
- **Testing:** pytest & HTTPX TestClient
- **Containerization:** Docker Compose

---

## Getting Started

### 1. Prerequisites
- Python 3.11+ (or Python 3.14)
- Docker & Docker Compose (optional for local database)

### 2. Virtual Environment & Dependencies
```powershell
# From project root
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### 3. Environment Variables
Copy the template configuration:
```powershell
Copy-Item backend\.env.example backend\.env
```

### 4. Running the Backend Server
```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
- Interactive API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative API Documentation (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 5. Running Tests
```powershell
cd backend
pytest
```

### 6. Starting PostgreSQL with Docker Compose
```powershell
docker compose up -d db
```
