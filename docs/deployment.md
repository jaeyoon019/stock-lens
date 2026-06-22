# Deployment

## Docker Compose (recommended)

The primary way to run stock-lens. One command starts the full backend stack.

### Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| `db` | `postgres:16-alpine` | 5432 | Primary database |
| `backend` | `python:3.13-slim` (built locally) | 8000 | FastAPI + Alembic |

Frontend is not containerized yet — run it with `npm run dev` (see [development.md](development.md)).

### Start

```bash
# First run — build backend image and start all services
docker compose up -d --build

# Subsequent runs
docker compose up -d
```

On startup the backend container automatically runs:
```
alembic upgrade head   ← apply any pending migrations
uvicorn app.main:app   ← start the API server
```

> The Dockerfile `CMD` defines this startup sequence as the default.
> Docker Compose's `command:` override adds `--reload` for development; the `CMD` is used as-is when running the image standalone (`docker run`).

### Stop

```bash
docker compose down          # stop containers, keep DB volume
docker compose down -v       # stop containers AND delete DB volume (full reset)
```

### Logs

```bash
docker compose logs -f backend
docker compose logs -f db
```

### Environment variables

The backend reads from `backend/.env` (mounted via `env_file`).
Copy the example and fill in your values before starting:

```bash
cp backend/.env.example backend/.env
# edit DATABASE_URL, OPENAI_API_KEY, CRAWL_TICKERS
```

`backend/.env` is listed in `.gitignore` and must never be committed.

---

## GitHub Actions — Daily Crawler

File: [`.github/workflows/daily_crawler.yml`](../.github/workflows/daily_crawler.yml)

### Trigger

```yaml
on:
  schedule:
    - cron: '0 22 * * *'   # daily at 07:00 KST (UTC 22:00)
  workflow_dispatch:        # manual trigger from GitHub UI
```

### Job steps

```
checkout → setup Python 3.13 → pip install → alembic upgrade head
→ python crawler/main.py
→ python -m app.services.report_generator
→ python -m app.ai.evaluator
```

PostgreSQL runs as a service container within the job — no external DB needed.

### Required secrets

Set these in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `CRAWL_TICKERS` | Comma-separated tickers, e.g. `AAPL,NVDA,005930,000660` |

```bash
# Set via GitHub CLI
gh secret set OPENAI_API_KEY
gh secret set CRAWL_TICKERS
```

### Manual trigger

```bash
gh workflow run daily_crawler.yml --repo jaeyoon019/stock-lens
```

Or use **Actions → Daily Crawler → Run workflow** in the GitHub UI.

---

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | `postgresql+asyncpg://user:pw@host/db` |
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model for report generation and evaluation |
| `CRAWL_TICKERS` | No | `AAPL,NVDA` | Comma-separated list of tickers to crawl |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

### Docker Compose vs GitHub Actions DATABASE_URL

| Environment | `DATABASE_URL` |
|-------------|----------------|
| Docker Compose | `postgresql+asyncpg://stocklens:stocklens@db/stocklens` (`db` = service name) |
| GitHub Actions | `postgresql+asyncpg://stocklens:stocklens@localhost/stocklens` (service container on localhost) |
| Local (no Docker) | `postgresql+asyncpg://postgres:postgres@localhost:5432/stocklens` |

---

## Dockerfile

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

The `CMD` is the production default. Docker Compose overrides it with `--reload` for live-reloading during development.
The source directory (`./backend`) is also mounted as a volume in Docker Compose,
so code changes take effect without rebuilding the image.

---

## Healthcheck

The `db` service includes a PostgreSQL healthcheck. The `backend` service only starts
after the DB is healthy:

```yaml
depends_on:
  db:
    condition: service_healthy
```

API-level health endpoint:
```
GET http://localhost:8000/health
→ {"status": "ok"}
```
