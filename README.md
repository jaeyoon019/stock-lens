# stock-lens

> AI-powered investment research assistant — collects financial news, generates structured bull/bear reports per ticker, and evaluates output quality automatically.

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Overview

**stock-lens** is a personal AI research assistant for stock market analysis built as a portfolio project.

Core capabilities:
- Multi-source news crawling with deduplication (Yahoo Finance RSS, Naver Finance)
- Structured AI report generation (bull/bear points, confidence score) via OpenAI Structured Output
- LLM-as-judge evaluation pipeline to track report quality over time
- Daily automation via GitHub Actions
- React dashboard with ticker search and report history

---

## Architecture

```
News Sources (Yahoo Finance RSS, Naver Finance)
        │
        ▼
Crawler (Python)          ← runs daily via GitHub Actions
        │  dedup by url_hash
        ▼
PostgreSQL
  stocks / articles / reports / evaluations
        │
        ▼
Report Generator          ← OpenAI API + Pydantic Structured Output
        │
        ▼
LLM Evaluator             ← LLM-as-judge, score stored in evaluations table
        │
        ▼
FastAPI REST API
        │
        ▼
React Dashboard           ← TanStack Query + Recharts + TailwindCSS
```

---

## Tech Stack

| Layer     | Technology                                          |
|-----------|-----------------------------------------------------|
| Language  | Python 3.13                                         |
| Backend   | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2       |
| AI        | OpenAI API (structured output), LlamaIndex (Phase 2)|
| Database  | PostgreSQL 16                                       |
| Frontend  | React 18, TypeScript, Vite, TanStack Query, Recharts, TailwindCSS |
| Infra     | Docker Compose, GitHub Actions                      |

---

## Project Structure

```
stock-lens/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI routers (stocks.py, reports.py)
│   │   ├── core/            # config.py, database.py
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic v2 request/response schemas
│   │   ├── services/        # report_generator.py
│   │   ├── ai/              # evaluator.py, prompts.py
│   │   └── main.py
│   ├── alembic/             # DB migrations
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── crawler/
│   ├── collectors/          # yahoo.py, naver.py
│   ├── parsers/             # article_parser.py
│   ├── jobs/                # scheduler.py
│   └── main.py
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── hooks/
│       ├── services/        # api.ts (axios client)
│       └── types/           # TypeScript interfaces
├── docs/
│   ├── ai-pipeline.md       # Report generation + LLM evaluation design
│   ├── api.md               # REST API reference
│   ├── database.md          # Schema + Alembic migration guide
│   ├── deployment.md        # Docker Compose + GitHub Actions
│   ├── development.md       # Local dev setup
│   ├── github-setup.md      # Labels, milestones, secrets
│   ├── testing.md           # Test guide
│   └── architecture/
│       ├── overview.md      # Component diagram
│       ├── data-flow.md     # End-to-end data flow
│       └── erd.mmd          # Mermaid ERD
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│       └── daily_crawler.yml
├── CLAUDE.md
├── docker-compose.yml
└── README.md
```

---

## Database Schema

Full ERD: [`docs/architecture/erd.mmd`](docs/architecture/erd.mmd) (render at [mermaid.live](https://mermaid.live))

| Table         | Description                                                  |
|---------------|--------------------------------------------------------------|
| `stocks`      | Ticker metadata (ticker, name, market, sector)               |
| `articles`    | Crawled news articles (deduplicated by url_hash, AI summary) |
| `reports`     | Daily bull/bear report per ticker + confidence_score         |
| `evaluations` | LLM-as-judge scores and feedback (0.0–1.0)                   |

---

## Environment Variables

See `.env.example`. Never commit the actual `.env` file.

| Variable           | Description                   | Example                                     |
|--------------------|-------------------------------|---------------------------------------------|
| `DATABASE_URL`     | PostgreSQL connection string  | `postgresql+asyncpg://user:pw@db/stocklens` |
| `OPENAI_API_KEY`   | OpenAI API key                | `sk-...`                                    |
| `OPENAI_MODEL`     | Model to use                  | `gpt-4o-mini`                               |
| `CRAWL_TICKERS`    | Tickers to crawl (comma-sep)  | `AAPL,005930,NVDA`                          |
| `LOG_LEVEL`        | Log level                     | `INFO`                                      |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- OpenAI API key

### 1. Clone & configure

```bash
git clone https://github.com/jaeyoon019/stock-lens.git
cd stock-lens
cp backend/.env.example backend/.env
# Fill in OPENAI_API_KEY and CRAWL_TICKERS in .env
```

### 2. Start services

```bash
docker compose up -d
```

This single command starts PostgreSQL + FastAPI + runs DB migrations.

### 3. Frontend (dev mode)

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at `http://localhost:5173`.

### 4. Run crawler manually

```bash
docker compose exec backend python -m crawler.main
```

---

## OpenAI Cost Estimate

| Item               | Model        | Est. tokens/day | Est. cost/month |
|--------------------|--------------|-----------------|-----------------|
| News summarization | gpt-4o-mini  | ~50k tokens     | ~$0.03          |
| Report generation  | gpt-4o-mini  | ~30k tokens     | ~$0.02          |
| LLM evaluation     | gpt-4o-mini  | ~20k tokens     | ~$0.01          |
| **Total**          |              |                 | **~$0.06/mo**   |

Estimate based on ~10 tickers. Actual cost varies with news volume.

---

## Data Sources

| Source            | Method       | Schedule        | Notes                         |
|-------------------|--------------|-----------------|-------------------------------|
| Yahoo Finance RSS | RSS parsing  | Daily 07:00 KST | robots.txt compliant          |
| Naver Finance     | HTML parsing | Daily 07:00 KST | 1s delay, personal use only   |

This is a personal learning project. Collected data is not redistributed.

---

## Evaluation Framework

```python
# Every generated report is automatically evaluated
{
  "judge_score": 0.82,   # 0.0 – 1.0
  "judge_feedback": "Bull points well-supported. Bear section lacks specificity.",
  "model_used": "gpt-4o-mini"
}
```

Scores are stored in the `evaluations` table, enabling time-series tracking of prompt improvement.

---

## Roadmap

- [x] Phase 0 — Project design and documentation
- [ ] Phase 1 — MVP: news crawling + AI reports + dashboard (Week 1–3)
- [ ] Phase 2 — RAG: vector DB + filing analysis (Week 4–7)
- [ ] Phase 3 — Agent: LangGraph multi-agent + chatbot (Week 8+)

---

## License

MIT
