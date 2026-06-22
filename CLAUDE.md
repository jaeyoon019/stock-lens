# CLAUDE.md — stock-lens

## Project overview

AI-powered stock research assistant. Crawls financial news daily, generates structured bull/bear reports per ticker via OpenAI, and evaluates report quality with an LLM-as-judge pipeline. Built as a portfolio project.

## Current phase status

| Component | Status |
|---|---|
| FastAPI read endpoints (`/stocks`, `/reports`) | Implemented |
| Yahoo Finance RSS crawler | Implemented |
| SQLAlchemy models + Alembic migrations | Implemented |
| Naver Finance crawler | **Stub** — `crawler/collectors/naver.py` |
| Report generator | **Stub** — `backend/app/services/report_generator.py` |
| LLM evaluator | **Stub** — `backend/app/ai/evaluator.py` |
| DB upsert in crawler | **Stub** — `crawler/main.py` (TODO comment) |
| React frontend | Scaffold only |

Do not treat stubs as implemented. Check the file before assuming functionality exists.

## Tech stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, asyncpg
- **AI:** OpenAI API — use `client.beta.chat.completions.parse()` with a Pydantic `response_format` (Structured Output), not JSON mode
- **Database:** PostgreSQL 16
- **Infra:** Docker Compose, GitHub Actions (daily cron at UTC 22:00 = KST 07:00)
- **Frontend:** React 18, TypeScript, Vite, TanStack Query, Recharts, TailwindCSS

## Repository structure

```
stock-lens/
├── backend/
│   ├── app/
│   │   ├── ai/              # evaluator.py, prompts.py
│   │   ├── api/v1/          # stocks.py, reports.py
│   │   ├── core/            # config.py, database.py
│   │   ├── models/          # models.py (SQLAlchemy ORM)
│   │   ├── schemas/         # report.py (Pydantic)
│   │   └── services/        # report_generator.py
│   ├── alembic/versions/    # migration files — always commit these
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                 # never commit — in .gitignore
├── crawler/
│   ├── collectors/          # yahoo.py, naver.py
│   ├── parsers/             # article_parser.py
│   └── main.py
├── frontend/src/
├── docs/
├── docker-compose.yml
└── .github/workflows/daily_crawler.yml
```

## Code rules

### Python / FastAPI

- **Always type path parameters with their exact domain type.** UUID path params must be `UUID`, not `str`. FastAPI validates at the boundary; `str` bypasses it and lets malformed input reach the DB.
- **Use `scalar_one_or_none()` for single-row queries**, raise `HTTPException(404)` when `None`.
- **All DB access is async.** Use `AsyncSession`, `await db.execute(...)`. Never use sync SQLAlchemy.
- **Pydantic v2 syntax only.** Use `model_config = ConfigDict(...)`, not the inner `class Config`.
- **Use `UUID(as_uuid=True)` for all UUID columns** in SQLAlchemy models — do not use `String` for UUIDs.

### AI pipeline

- **Report Generator must use Structured Output:** `client.beta.chat.completions.parse(response_format=ReportOutput)`. Never parse JSON manually.
- **LLM Evaluator must also use Structured Output** for `judge_score` and `judge_feedback` — do not parse free-text responses.
- **One OpenAI call per ticker per step.** Keep report generation and evaluation as separate sequential steps.

### Database / migrations

- **Always run `alembic revision --autogenerate` after changing `models.py`**, then review the generated file — autogenerate misses check constraints and custom indexes.
- **Commit `models.py` and the migration file together** in the same commit.
- **Deduplication key is `url_hash` (SHA-256 of URL)**, not the URL itself. Use `ON CONFLICT (url_hash) DO NOTHING`.
- **One report per ticker per calendar day** — enforced by `UNIQUE(stock_id, report_date)`.

### Docker

- The `Dockerfile` CMD provides the production default (`alembic upgrade head && uvicorn`).
- `docker-compose.yml` overrides CMD with `--reload` for development.
- Never add `--reload` to the Dockerfile CMD.
- The backend container depends on `db: condition: service_healthy` — do not remove this.

### Dependencies

- **Never remove `uvloop>=0.21.0`** from `requirements.txt` — it is explicitly pinned to ensure Python 3.13 compatibility for `uvicorn[standard]`'s transitive dependency.
- **asyncpg must stay at `>=0.30.0`** — earlier versions do not build on Python 3.13.
- When adding a new dependency that has C extensions, verify it has Python 3.13 wheels before pinning.

## PR workflow

- Always work on a feature branch, never commit directly to `main`.
- Branch naming: `fix/<short-description>` or `feat/<short-description>`.
- Use squash merge when merging to `main`.
- Delete the branch after merging.
- Never force-push to `main`.

## Common commands

```bash
# Start full stack
docker compose up -d --build

# Run migrations manually
docker compose exec backend alembic upgrade head

# Run crawler manually
python crawler/main.py

# Run AI pipeline manually
cd backend
python -m app.services.report_generator
python -m app.ai.evaluator

# Run tests (requires DB running)
cd backend && pytest

# Frontend dev server
cd frontend && npm run dev

# Trigger CI manually
gh workflow run daily_crawler.yml --repo jaeyoon019/stock-lens
```

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | Must use `postgresql+asyncpg://` driver prefix |
| `OPENAI_API_KEY` | Yes | — | Set as GitHub Actions secret |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Used for both report generation and evaluation |
| `CRAWL_TICKERS` | No | `AAPL,NVDA` | Comma-separated; set as GitHub Actions secret |
| `LOG_LEVEL` | No | `INFO` | |

Never commit `backend/.env`.

## Things to avoid

- Do not use `str` for UUID path parameters in FastAPI — always use `uuid.UUID`.
- Do not parse OpenAI responses as free text — always use Structured Output with a Pydantic model.
- Do not add mock DB access in tests — tests use a real database connection.
- Do not run the crawler or AI pipeline as part of `pytest`.
- Do not add `--reload` to the Dockerfile CMD.
- Do not commit `.env`, credentials, or API keys.
- Do not skip Alembic migrations by directly modifying the DB schema.
