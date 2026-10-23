<div align="center">

<br/>

```
╔═══════════════════════════════════════════════════════════════════╗
║        SQL QUERY OPTIMIZER & PERFORMANCE INTELLIGENCE STUDIO      ║
╚═══════════════════════════════════════════════════════════════════╝
```

<h3>A full-stack PostgreSQL performance intelligence platform for developers who care about query efficiency</h3>

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-f97316?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-f97316?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6.x-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind-v4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)

<br/>

![Tests](https://img.shields.io/badge/Backend_Tests-108_passing-22c55e?style=for-the-badge)
![Tests](https://img.shields.io/badge/Frontend_Tests-14_passing-22c55e?style=for-the-badge)
![Build](https://img.shields.io/badge/Build-Passing-22c55e?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-f97316?style=for-the-badge)

<br/>

</div>

---

## ✦ Overview

**SQL Query Optimizer & Performance Intelligence Studio** is a comprehensive, full-stack software engineering project that goes beyond simple query formatting — it delivers a genuine **PostgreSQL performance intelligence platform**. Write a SQL query, and the platform gives you:

- A detailed **execution plan analysis** with bottleneck identification
- **AI-guided index recommendations** ranked by estimated impact
- **Conservative SQL rewrites** that are provably safe and correct
- **Safe benchmarking** with historical run comparison
- **Result equivalence checks** between original and rewritten queries
- A **performance scoring system** with optimizer evaluation metrics

Built across **8 development phases**, from database foundation to UI/UX polish, this project demonstrates full-stack product thinking: robust engineering on the backend, and a polished, premium developer experience on the frontend.

---

## ✦ Feature Showcase

### 🔍 Query Analysis Engine
The heart of the platform. Submit any SQL `SELECT` query and receive:
- Full `EXPLAIN ANALYZE` plan parsed and structured
- Node-level cost/row estimates vs actual performance
- Bottleneck identification (sequential scans, hash joins, sort nodes)
- Plan summary cards with key metrics (total cost, rows, planning time, execution time)

### 🗂️ Intelligent Index Advisor
- Scans query predicates, join conditions, and ORDER BY clauses
- Recommends missing indexes with estimated selectivity gains
- Ranks recommendations by projected impact (High / Medium / Low)
- Generates ready-to-copy `CREATE INDEX` DDL statements

### ✏️ Conservative SQL Rewriter
- Applies rule-based, semantics-preserving rewrites (no hallucinations)
- Each transformation explained with before/after comparison
- Zero destructive rewrites — all changes are reversible and auditable
- Powered by `sqlglot` for AST-level SQL parsing

### ⚡ Safe Query Benchmarking
- Runs queries inside `READ ONLY` transactions (zero side effects)
- Configurable iteration count for statistical stability
- Calculates mean, median, min, max, and standard deviation
- Historical benchmark storage and trend comparison over time

### ✅ Result Equivalence Checker
- Compares original vs rewritten query result sets row-by-row
- Schema-aware column ordering normalization
- Reports mismatches with detailed diff output
- Prevents shipping rewrites that silently change behavior

### 📊 Optimizer Evaluation & Scoring
- Composite performance score (0–100) across multiple dimensions
- Plan quality, index usage, rewrite safety, and execution efficiency
- Readiness checklist for production deployment confidence
- Historical score tracking with regression detection

---

## ✦ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React 19)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Query       │  │  Plan        │  │  Benchmark &     │  │
│  │  Editor      │  │  Visualizer  │  │  Evaluation      │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Index       │  │  SQL Rewrite │  │  Equivalence     │  │
│  │  Advisor     │  │  Diff View   │  │  Checker         │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│               TanStack Query · React Router DOM             │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / REST API
┌───────────────────────────▼─────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│                                                             │
│  /api/analyze ──► PlanAnalyzer ──► ExplainService           │
│  /api/index-advisor ──► IndexAdvisor                        │
│  /api/rewrites ──► SQLRewriter (sqlglot AST)                │
│  /api/benchmark ──► BenchmarkService (READ ONLY txn)        │
│  /api/evaluate ──► EvaluationService + EquivalenceService   │
│  /api/readiness ──► ReadinessChecker                        │
│                                                             │
│  SQLAlchemy ORM · Alembic Migrations · Pydantic Schemas     │
└───────────────────────────┬─────────────────────────────────┘
                            │ psycopg3 (async)
┌───────────────────────────▼─────────────────────────────────┐
│               PostgreSQL 16 (Docker)                        │
│                                                             │
│  Sample Schema: orders, customers, products, order_items    │
│  Benchmark History · Analysis Results · Evaluation Scores   │
└─────────────────────────────────────────────────────────────┘
```

---

## ✦ Tech Stack

### Backend

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI 0.115 | Async REST API with OpenAPI docs |
| **Database** | PostgreSQL 16 | Primary data store & query target |
| **ORM** | SQLAlchemy 2.x | Async models and queries |
| **Migrations** | Alembic 1.13 | Schema versioning (8 migration files) |
| **Driver** | psycopg3 (binary) | Modern async PostgreSQL driver |
| **SQL Parser** | sqlglot 25.x | AST-level SQL analysis and rewriting |
| **Validation** | Pydantic v2 | Request/response schema enforcement |
| **Server** | Uvicorn (ASGI) | Production-grade async server |
| **Testing** | pytest + httpx | 108 passing integration tests |

### Frontend

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | React 19 | Component-based UI |
| **Language** | TypeScript 5.x | Type-safe application logic |
| **Build Tool** | Vite 6.x | Lightning-fast dev server and builds |
| **Styling** | Tailwind CSS v4 | Utility-first design system |
| **State** | TanStack Query | Server state, caching, refetching |
| **Routing** | React Router DOM | Multi-page navigation |
| **Testing** | Vitest + Testing Library | 14 passing component tests |

---

## ✦ UI Design — Sandal & Orange Theme

The frontend features a handcrafted **Sandal Cream & Dark Sandalwood** dual-theme design system — a distinctive, non-generic aesthetic designed to look and feel like a real professional developer tool.

### 🌅 Sandal Cream (Light Mode)
- **Canvas**: `#f6f1e7` — warm parchment background
- **Accent**: `#ea580c` — saffron orange for interactive elements
- **Surface**: `#fdf8f0` — elevated card backgrounds
- **Typography**: Sandalwood timber `#3d2b1f` — rich, readable contrast

### 🌙 Dark Sandalwood (Dark Mode)
- **Canvas**: `#1a1008` — deep espresso background
- **Surface**: `#2a1a0e` — raised panel surfaces
- **Accent**: `#fb923c` — glowing ember orange
- **Typography**: `#f6f1e7` — cream text on dark wood

> Toggle between themes with the **☀️ / 🌙** button in the top-right header. Your preference is persisted in `localStorage`.

---

## ✦ Project Structure

```
sql-query-optimizer/
│
├── backend/
│   ├── app/
│   │   ├── api/                    # Route handlers
│   │   │   ├── analysis.py         # /api/analyze endpoint
│   │   │   ├── benchmarks.py       # /api/benchmark endpoint
│   │   │   ├── evaluations.py      # /api/evaluate endpoint
│   │   │   └── validation.py       # /api/validate endpoint
│   │   ├── services/               # Business logic
│   │   │   ├── plan_analyzer.py    # EXPLAIN ANALYZE parser
│   │   │   ├── explain_service.py  # Query execution wrapper
│   │   │   ├── index_advisor.py    # Index recommendation engine
│   │   │   ├── sql_rewriter.py     # Conservative rewrite rules
│   │   │   ├── sql_validator.py    # SQL safety validation
│   │   │   ├── benchmark_service.py# Safe benchmarking engine
│   │   │   ├── equivalence_service.py # Result comparison
│   │   │   ├── evaluation_service.py  # Scoring & evaluation
│   │   │   └── plan_comparison.py  # Plan diff utility
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── db/                     # Database session management
│   │   └── main.py                 # FastAPI app entry point
│   ├── alembic/                    # Database migrations (8 versions)
│   ├── tests/                      # 108 pytest integration tests
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── editor/             # QueryEditor with syntax hints
│   │   │   ├── analysis/           # PlanSummaryCards, NodeTree
│   │   │   ├── recommendations/    # IndexRecommendationsView
│   │   │   ├── rewrites/           # RewriteDiffView
│   │   │   ├── benchmark/          # BenchmarkRunner, HistoryChart
│   │   │   ├── evaluation/         # ScoreGauge, EvalReport
│   │   │   ├── plan/               # PlanVisualizer
│   │   │   └── layout/             # Header (with theme toggle), Sidebar
│   │   ├── services/               # API client functions
│   │   ├── types/                  # TypeScript interfaces
│   │   ├── data/                   # Static sample queries
│   │   ├── index.css               # Sandal & Orange theme system
│   │   └── App.tsx                 # Root app with router
│   ├── index.html                  # Anti-flash theme script
│   └── vite.config.ts
│
├── database/                       # Sample schema + seed data
├── docker-compose.yml              # PostgreSQL service definition
└── README.md
```

---

## ✦ Getting Started

### Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| Python | 3.11+ | `python --version` |
| Node.js | 20+ | `node --version` |
| PostgreSQL | 16+ | Via Docker or local install |
| Docker (optional) | Latest | For the included compose file |

---

### 1 — Clone the Repository

```bash
git clone https://github.com/your-username/sql-query-optimizer.git
cd sql-query-optimizer
```

---

### 2 — Start PostgreSQL

**Using Docker (recommended):**
```bash
docker-compose up -d
```

The compose file starts a PostgreSQL 16 container on port `5432` with credentials pre-configured for the backend `.env`.

**Using a local PostgreSQL install:**
Create a database and user manually, then update `backend/.env` accordingly.

---

### 3 — Configure the Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Copy the environment template and fill in your database credentials:

```bash
cp .env.example .env
```

**`backend/.env` reference:**
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/sql_optimizer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=sql_optimizer
```

---

### 4 — Run Database Migrations

```bash
cd backend

# Apply all migration versions
alembic upgrade head
```

This creates all tables: analysis results, benchmark history, evaluation scores, index recommendations, and the sample schema (orders, customers, products, order_items).

---

### 5 — Start the Backend Server

```bash
cd backend

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now live at **`http://localhost:8000`**.

Interactive API documentation: **`http://localhost:8000/docs`** (Swagger UI)

---

### 6 — Start the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the Vite dev server
npm run dev
```

The app is now running at **`http://localhost:5173`**.

---

## ✦ API Reference

All endpoints accept and return JSON. The base URL is `http://localhost:8000`.

### `POST /api/analyze`
Analyzes a SQL query using `EXPLAIN ANALYZE` and returns a structured plan.

**Request:**
```json
{
  "sql": "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id WHERE o.status = 'pending'",
  "database_url": "postgresql+psycopg://..."
}
```

**Response includes:**
- `plan_nodes` — full node tree with costs and actuals
- `summary` — total cost, rows, planning time, execution time
- `bottlenecks` — identified slow nodes
- `index_recommendations` — missing index suggestions
- `rewrites` — conservative SQL transformations

---

### `POST /api/benchmark`
Runs the query multiple times in a `READ ONLY` transaction and returns timing statistics.

```json
{
  "sql": "SELECT ...",
  "iterations": 10
}
```

**Returns:** `mean_ms`, `median_ms`, `min_ms`, `max_ms`, `std_dev_ms`, `run_id`

---

### `POST /api/evaluate`
Runs the full evaluation pipeline and returns a composite performance score.

```json
{
  "original_sql": "SELECT ...",
  "rewritten_sql": "SELECT ..."
}
```

**Returns:** `score` (0–100), `dimensions` breakdown, `equivalence_result`, `recommendation`

---

### `GET /api/benchmark/history`
Returns historical benchmark runs for trend analysis.

---

### `POST /api/validate`
Validates SQL syntax and checks for unsafe operations (DDL, DML, DROP, etc.)

---

## ✦ Running Tests

### Backend — 108 Tests
```bash
cd backend

# Activate virtual environment first
pytest -v

# Quiet summary
pytest --tb=short -q
```

### Frontend — 14 Tests
```bash
cd frontend

npm test

# Run once without watch mode
npm run test:run
```

### Production Build Verification
```bash
cd frontend

npm run build
# Zero TypeScript errors, optimized bundle output
```

---

## ✦ Development Phases

This project was built in **8 structured phases**, each building on the last:

| Phase | Title | Key Deliverables |
|-------|-------|-----------------|
| **1** | Foundation | PostgreSQL schema, Docker setup, Alembic migrations |
| **2** | Query Analysis Engine | `EXPLAIN ANALYZE` parsing, plan node tree, bottleneck detection |
| **3** | Index Advisor & Rewriter | Missing index detection, conservative SQL rewrites via sqlglot |
| **4** | Performance Intelligence Studio | React frontend, plan visualizer, recommendation UI |
| **5** | Safe Benchmarking | READ-ONLY transaction benchmarks, historical storage, stats |
| **6** | Result Equivalence Checking | Row-level result comparison, schema normalization, diff reporting |
| **7** | Optimizer Evaluation & Scoring | Composite score, dimension breakdown, readiness checklist |
| **8** | Hardening & UI Polish | Security review, 108 passing tests, Sandal & Orange theme system |

---

## ✦ Design Decisions

### Why `READ ONLY` Transactions for Benchmarking?
Benchmarking `UPDATE` or `DELETE` statements against production-like data could cause irreversible data loss. Wrapping all benchmark runs in `SET TRANSACTION READ ONLY` means the system will reject any mutating SQL before execution — making it safe to benchmark against real databases.

### Why sqlglot for Rewrites (not LLMs)?
LLM-based SQL rewriting is non-deterministic and can silently alter query semantics. `sqlglot` operates on the AST, allowing rule-based, mathematically provable transformations. Every rewrite in this system can be audited, reversed, and explained.

### Why Equivalence Checking Matters?
A rewritten query that returns different results is worse than no rewrite at all. The equivalence service normalizes column ordering, handles NULL semantics, and compares result sets row-by-row before any rewrite is flagged as safe.

### Why Pydantic v2 for Schemas?
Pydantic v2 gives us runtime type validation, serialization performance, and self-documenting OpenAPI schemas — all critical for a developer tool where the API contract is part of the product.

---

## ✦ Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/sql_optimizer` | SQLAlchemy async connection string |
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `POSTGRES_DB` | `sql_optimizer` | Database name |

### Frontend
The frontend proxies API requests to `http://localhost:8000` via the Vite dev server config. No additional environment variables are required for development.

---

## ✦ Docker Reference

The included `docker-compose.yml` starts a pre-configured PostgreSQL instance:

```bash
# Start
docker-compose up -d

# Check logs
docker-compose logs -f postgres

# Stop and remove volumes (deletes all data)
docker-compose down -v

# Stop without removing data
docker-compose stop
```

---

## ✦ Roadmap

- [ ] **AI-assisted rewrites** — LLM suggestions alongside rule-based rewrites, with equivalence gating
- [ ] **Multi-database support** — MySQL and SQLite adapters via pluggable explain parsers
- [ ] **Visual plan diff** — Side-by-side plan tree comparison between original and rewritten queries
- [ ] **Continuous monitoring** — Scheduled background benchmarks with Slack/email alerts on regressions
- [ ] **Query history** — Per-user query library with tagging and annotation support
- [ ] **Export reports** — PDF/Markdown export of full analysis, scores, and recommendations

---

## ✦ Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit with descriptive messages: `git commit -m "feat: add plan diff visualizer"`
4. Push and open a Pull Request

**Before submitting:**
- [ ] All 108 backend tests pass (`pytest -q`)
- [ ] All 14 frontend tests pass (`npm test`)
- [ ] Frontend builds cleanly (`npm run build`)
- [ ] No TypeScript errors
- [ ] New services have corresponding tests

---

## ✦ License

This project is released under the **MIT License**. See [`LICENSE`](./LICENSE) for details.

---

<div align="center">

<br/>

**Built with fire and a deep appreciation for query performance**

*SQL Query Optimizer & Performance Intelligence Studio*

*FastAPI · PostgreSQL · React · TypeScript · Tailwind CSS v4*

<br/>

</div>
