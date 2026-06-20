# System Architecture Overview

## Purpose

stock-lens automates the full cycle of equity research:
collect raw news → generate structured bull/bear reports → evaluate report quality automatically.
All steps run daily without human intervention via GitHub Actions.

---

## High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     Data Sources                        │
│   Yahoo Finance RSS          Naver Finance (HTML)       │
└────────────────┬────────────────────┬───────────────────┘
                 │                    │
                 ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                  Crawler  (Python)                      │
│  collectors/yahoo.py        collectors/naver.py         │
│  parsers/article_parser.py                              │
│  • SHA-256 url_hash deduplication                       │
│  • Runs daily at 07:00 KST via GitHub Actions           │
└──────────────────────────┬──────────────────────────────┘
                           │ upsert
                           ▼
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL 16  (Docker)                    │
│   stocks │ articles │ reports │ evaluations             │
└──────────┬───────────────────────────┬──────────────────┘
           │ read articles             │ write reports / evaluations
           ▼                           │
┌──────────────────────┐               │
│   Report Generator   │               │
│  (OpenAI gpt-4o-mini)│               │
│  Structured Output   │───────────────┘
│  → bull/bear points  │
│  → confidence score  │
└──────────┬───────────┘
           │ generated report
           ▼
┌──────────────────────┐
│   LLM Evaluator      │
│  (OpenAI gpt-4o-mini)│
│  LLM-as-judge        │
│  → judge_score 0–1   │
│  → judge_feedback    │
└──────────────────────┘
                           ▲ read
┌──────────────────────────┴──────────────────────────────┐
│               FastAPI  (port 8000)                      │
│   GET /api/v1/stocks                                    │
│   GET /api/v1/reports?ticker=&from_date=                │
│   GET /api/v1/reports/{id}                              │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / JSON
                           ▼
┌─────────────────────────────────────────────────────────┐
│           React Dashboard  (port 5173)                  │
│   TanStack Query  •  Recharts  •  TailwindCSS           │
│   • Ticker search                                       │
│   • Report viewer                                       │
│   • Confidence score time-series chart                  │
└─────────────────────────────────────────────────────────┘
```

---

## Components

### Crawler
- **Location:** `crawler/`
- **Runtime:** GitHub Actions (`ubuntu-latest`), daily cron
- **Responsibility:** Fetch raw articles from news sources, deduplicate by SHA-256 of URL, upsert into `articles` table
- **Key constraint:** 1-second delay between Naver Finance requests; robots.txt compliant for Yahoo

### PostgreSQL
- **Version:** 16-alpine (Docker)
- **Four tables:** `stocks`, `articles`, `reports`, `evaluations`
- **Deduplication:** `UNIQUE` constraint on `articles.url_hash` — concurrent crawls are safe
- **Schema reference:** [`erd.mmd`](erd.mmd)

### Report Generator
- **Location:** `backend/app/services/report_generator.py`
- **Model:** `gpt-4o-mini` (configurable via `OPENAI_MODEL`)
- **Output format:** OpenAI Structured Output → `ReportOutput` Pydantic schema
- **Fields produced:** `bull_points[]`, `bear_points[]`, `overall_summary`, `confidence_score`
- **Runs after:** crawler completes each day

### LLM Evaluator
- **Location:** `backend/app/ai/evaluator.py`
- **Pattern:** LLM-as-judge — a second independent LLM call scores the generated report
- **Output:** `judge_score` (0.0–1.0), `judge_feedback` (text), stored in `evaluations`
- **Purpose:** Track prompt improvement over time without human annotation

### FastAPI Backend
- **Location:** `backend/app/`
- **Port:** 8000
- **DB access:** SQLAlchemy 2.0 async (`asyncpg`)
- **Migrations:** Alembic (runs automatically at container start)
- **CORS:** allows `http://localhost:5173` (frontend dev server)

### React Dashboard
- **Location:** `frontend/`
- **Port:** 5173 (Vite dev server)
- **Data fetching:** TanStack Query with `/api` proxy → FastAPI
- **Charts:** Recharts for confidence_score time-series
- **Styling:** TailwindCSS

---

## Tech Stack Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Async backend | FastAPI + asyncpg | Non-blocking DB I/O; keeps crawler and API on the same stack |
| ORM | SQLAlchemy 2.0 (async) | Type-safe, mature, aligns with Pydantic v2 |
| AI output format | OpenAI Structured Output | Guarantees schema compliance without prompt-engineering JSON |
| Deduplication | SHA-256 url_hash | Deterministic; works across restarts and concurrent runs |
| Evaluation | LLM-as-judge | Scalable quality signal without manual labeling |
| Infra | Docker Compose | Single command to start DB + backend; mirrors prod pattern |
| CI/CD | GitHub Actions | Free for public repos; native secret management |

---

## Deployment Topology

```
Local / GitHub Actions
├── docker-compose.yml
│   ├── db       (postgres:16-alpine, port 5432)
│   └── backend  (python:3.13-slim, port 8000)
│       └── on start: alembic upgrade head → uvicorn
└── frontend (npm run dev, port 5173)   ← dev only, not containerized yet
```

In GitHub Actions the PostgreSQL runs as a service container; the crawler and report generator run as sequential steps in the same job (see [`.github/workflows/daily_crawler.yml`](../../.github/workflows/daily_crawler.yml)).

---

## Phase Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Design, documentation, scaffold | Done |
| 1 | MVP — crawler + AI reports + dashboard | In progress |
| 2 | RAG — vector DB + filing analysis (LlamaIndex) | Planned |
| 3 | Agent — LangGraph multi-agent + chatbot | Planned |
