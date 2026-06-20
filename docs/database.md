# Database

PostgreSQL 16. Full ERD: [`docs/architecture/erd.mmd`](architecture/erd.mmd) (render at [mermaid.live](https://mermaid.live)).

---

## Tables

### `stocks`

Ticker registry. Seeded manually or via the crawler when a new ticker is first encountered.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | |
| `ticker` | VARCHAR(20) | UNIQUE, NOT NULL | e.g. `AAPL`, `005930` |
| `name` | VARCHAR(200) | NOT NULL | Company name |
| `market` | VARCHAR(20) | NOT NULL | `NASDAQ` \| `NYSE` \| `KRX` |
| `sector` | VARCHAR(100) | nullable | Industry sector |
| `created_at` | TIMESTAMP | server default `now()` | |
| `updated_at` | TIMESTAMP | server default `now()`, on update | |

---

### `articles`

Raw news articles collected by the crawler. Central dedup boundary.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | |
| `stock_id` | UUID | FK → `stocks.id`, NOT NULL | |
| `title` | VARCHAR(500) | NOT NULL | Article headline |
| `source` | VARCHAR(50) | NOT NULL | `yahoo` \| `naver` |
| `url` | VARCHAR(2000) | NOT NULL | Original article URL |
| `url_hash` | VARCHAR(64) | UNIQUE (`uq_articles_url_hash`), NOT NULL | SHA-256 of `url` |
| `content` | TEXT | nullable | Raw body text from RSS / scraper |
| `summary` | TEXT | nullable | AI-generated summary (Phase 1) |
| `sentiment` | VARCHAR(20) | nullable | `positive` \| `neutral` \| `negative` |
| `published_at` | TIMESTAMP | nullable | Original publication time |
| `created_at` | TIMESTAMP | server default `now()` | |

**Key design decision:** `url_hash` is the dedup key, not `url`, because URLs can vary in
trailing slashes and query parameters while pointing to the same article.
`ON CONFLICT (url_hash) DO NOTHING` makes crawler re-runs fully idempotent.

---

### `reports`

One AI-generated bull/bear report per ticker per calendar day.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | |
| `stock_id` | UUID | FK → `stocks.id`, NOT NULL | |
| `report_date` | DATE | NOT NULL | Calendar date of report |
| `bull_points` | JSON | NOT NULL, default `[]` | Bullish arguments (string array) |
| `bear_points` | JSON | NOT NULL, default `[]` | Bearish arguments (string array) |
| `overall_summary` | TEXT | NOT NULL | 2–3 sentence synthesis |
| `confidence_score` | FLOAT | NOT NULL | 0.0–1.0 |
| `article_count` | INTEGER | default `0` | Number of articles used |
| `created_at` | TIMESTAMP | server default `now()` | |

**Unique constraint:** `uq_reports_stock_date` on `(stock_id, report_date)` — guarantees
exactly one report per ticker per day. Re-running the pipeline on the same day is a no-op.

---

### `evaluations`

LLM-as-judge scores for each report. Multiple evaluations per report are allowed
(useful when re-evaluating after a prompt change).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | |
| `report_id` | UUID | FK → `reports.id`, NOT NULL | |
| `judge_score` | FLOAT | NOT NULL | 0.0–1.0 quality score |
| `judge_feedback` | TEXT | NOT NULL | Free-text critique from the judge |
| `model_used` | VARCHAR(100) | NOT NULL | e.g. `gpt-4o-mini` |
| `created_at` | TIMESTAMP | server default `now()` | |

---

## Relationships

```
stocks ──< articles      (one stock, many articles)
stocks ──< reports       (one stock, many reports — one per day)
reports ──< evaluations  (one report, many evaluations)
```

---

## Indexes

Beyond primary keys and the unique constraints listed above:

| Table | Index | Reason |
|-------|-------|--------|
| `articles` | `uq_articles_url_hash` (UNIQUE) | Dedup lookup on every crawler run |
| `reports` | `uq_reports_stock_date` (UNIQUE) | Idempotent daily insert |

Additional indexes to add when query volume grows (Phase 2+):
- `articles(stock_id, published_at DESC)` — fetch latest articles per ticker
- `reports(stock_id, report_date DESC)` — fetch report history per ticker
- `evaluations(report_id)` — fetch scores per report

---

## Migrations (Alembic)

Alembic manages all schema changes. Migrations live in `backend/alembic/versions/`.

### Common commands

```bash
cd backend

# Apply all pending migrations (runs automatically on docker compose up)
alembic upgrade head

# Generate a new migration after changing models.py
alembic revision --autogenerate -m "add articles sentiment index"

# Inspect current revision
alembic current

# Roll back one step
alembic downgrade -1
```

### Workflow for schema changes

```
1. Edit backend/app/models/models.py
2. alembic revision --autogenerate -m "describe the change"
3. Review the generated file in alembic/versions/ — autogenerate misses some things
   (e.g. check constraints, custom indexes)
4. alembic upgrade head
5. Commit both models.py and the new migration file together
```

### Running in Docker

```bash
# Migrations run automatically when the backend container starts:
# command: sh -c "alembic upgrade head && uvicorn app.main:app ..."

# To run manually inside the container:
docker compose exec backend alembic upgrade head
```

---

## Connection

Configured via `DATABASE_URL` environment variable.

| Environment | URL |
|-------------|-----|
| Docker Compose | `postgresql+asyncpg://stocklens:stocklens@db/stocklens` |
| GitHub Actions | `postgresql+asyncpg://stocklens:stocklens@localhost/stocklens` |
| Local (no Docker) | `postgresql+asyncpg://postgres:postgres@localhost:5432/stocklens` |

The `asyncpg` driver is required for SQLAlchemy async sessions. The sync `psycopg2` driver
is not compatible with the async engine used in this project.
