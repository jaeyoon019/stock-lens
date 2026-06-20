# Development Setup

Local development guide for running stock-lens without Docker.
For the quick Docker-based start, see the [README](../README.md).

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.13 | [python.org](https://www.python.org/downloads/) |
| PostgreSQL | 16 | [postgresql.org](https://www.postgresql.org/download/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| Git | any | |

---

## Backend

### 1. Create virtual environment

```bash
cd backend
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stocklens
OPENAI_API_KEY=sk-...          # required for report generation and evaluation
OPENAI_MODEL=gpt-4o-mini
CRAWL_TICKERS=AAPL,NVDA
LOG_LEVEL=INFO
```

### 4. Create the database

```bash
# Connect to PostgreSQL and create the database
psql -U postgres -c "CREATE DATABASE stocklens;"
```

### 5. Run migrations

```bash
cd backend
alembic upgrade head
```

### 6. Start the API server

```bash
uvicorn app.main:app --reload --port 8000
```

API available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at `http://localhost:5173`.

The Vite dev server proxies `/api/*` requests to `http://localhost:8000`,
so the backend must be running for data to load.

---

## Crawler

The crawler runs as a standalone script. It reads `CRAWL_TICKERS` from the environment.

```bash
# From the repo root
python crawler/main.py
```

Or with explicit tickers:

```bash
CRAWL_TICKERS=AAPL,NVDA python crawler/main.py
```

---

## Running the AI Pipeline Manually

```bash
cd backend

# 1. Generate reports for all tickers in CRAWL_TICKERS
python -m app.services.report_generator

# 2. Evaluate all reports that don't have a score yet
python -m app.ai.evaluator
```

---

## Running Tests

```bash
cd backend
pytest
```

Tests live in `backend/tests/`. The test suite uses a real database connection
(not mocks) — ensure the `stocklens` database is running before executing tests.

---

## Project Layout Quick Reference

```
stock-lens/
├── backend/
│   ├── .venv/               # not committed
│   ├── .env                 # not committed
│   ├── alembic.ini
│   ├── alembic/versions/    # migration files — commit these
│   ├── app/
│   │   ├── ai/              # evaluator.py, prompts.py
│   │   ├── api/v1/          # stocks.py, reports.py
│   │   ├── core/            # config.py, database.py
│   │   ├── models/          # models.py (SQLAlchemy ORM)
│   │   ├── schemas/         # report.py (Pydantic)
│   │   ├── services/        # report_generator.py
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── crawler/
│   ├── collectors/          # yahoo.py, naver.py
│   ├── parsers/             # article_parser.py
│   ├── jobs/                # scheduler.py
│   └── main.py
└── frontend/
    ├── src/
    │   ├── components/
    │   ├── hooks/
    │   ├── pages/
    │   ├── services/        # api.ts — axios client
    │   └── types/           # TypeScript interfaces
    ├── index.html
    ├── package.json
    └── vite.config.ts
```

---

## Common Issues

**`asyncpg` connection refused**
Ensure PostgreSQL is running on port 5432 and the database `stocklens` exists.
Check with `psql -U postgres -l`.

**`ModuleNotFoundError: app`**
Run uvicorn from inside the `backend/` directory, not the repo root.

**`alembic: No such command`**
Activate the virtual environment first: `source backend/.venv/bin/activate`.

**Vite proxy errors (`ECONNREFUSED`)**
The FastAPI backend must be running before starting `npm run dev`.
