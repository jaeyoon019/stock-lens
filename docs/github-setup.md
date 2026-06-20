# GitHub Milestones & Issues Setup Guide

## Prerequisites

```bash
# Verify GitHub CLI is installed
gh --version

# Authenticate
gh auth login

# Create and clone the repo
gh repo create jaeyoon019/stock-lens --public --clone
cd stock-lens
```

---

## Create Labels

```bash
gh label create "setup"      --color "BFD4F2" --description "Initial setup"
gh label create "db"         --color "5319E7" --description "Database / migrations"
gh label create "crawler"    --color "0075CA" --description "Data collection"
gh label create "ai"         --color "E4E669" --description "AI / LLM"
gh label create "evaluation" --color "D93F0B" --description "Evaluation pipeline"
gh label create "backend"    --color "0E8A16" --description "FastAPI / server"
gh label create "frontend"   --color "F9D0C4" --description "React / UI"
gh label create "infra"      --color "C5DEF5" --description "Docker / CI"
```

---

## Create Milestones

`gh milestone create` is not available in the official CLI — use `gh api` instead.

```bash
gh api repos/:owner/:repo/milestones \
  --method POST \
  --field title="Phase 1 — MVP" \
  --field description="News crawling + AI reports + dashboard"

gh api repos/:owner/:repo/milestones \
  --method POST \
  --field title="Phase 2 — RAG" \
  --field description="Vector DB + filing analysis"

gh api repos/:owner/:repo/milestones \
  --method POST \
  --field title="Phase 3 — Agent" \
  --field description="LangGraph multi-agent + chatbot"
```

Check milestone numbers:
```bash
gh api repos/:owner/:repo/milestones --jq '.[] | {number, title}'
```

---

## Create Phase 1 Issues

Replace `--milestone` number with the value returned by `gh api` above.

### Week 1 — Data collection + DB

```bash
gh issue create --title "[FEAT] Docker Compose PostgreSQL setup" \
  --body "Write docker-compose.yml with healthcheck" \
  --label "setup,infra" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] Define SQLAlchemy models (4 tables)" \
  --body "stocks, articles, reports, evaluations" \
  --label "db" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] Initial Alembic migration" \
  --body "alembic init + generate first revision" \
  --label "db" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] Yahoo Finance RSS crawler" \
  --body "feedparser-based, dedup by url_hash" \
  --label "crawler" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] Naver Finance crawler" \
  --body "requests + BeautifulSoup" \
  --label "crawler" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] DB upsert logic (article deduplication)" \
  --body "url_hash-based ON CONFLICT DO NOTHING" \
  --label "crawler,db" --milestone "Phase 1 — MVP"
```

### Week 2 — AI pipeline

```bash
gh issue create --title "[FEAT] OpenAI Structured Output report generator" \
  --body "bull_points, bear_points, overall_summary, confidence_score" \
  --label "ai" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] Define Pydantic v2 report schema" \
  --body "ReportOutput model, JSON mode" \
  --label "ai" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] LLM-as-judge evaluation pipeline" \
  --body "Score generated reports 0.0–1.0 via a second LLM call" \
  --label "ai,evaluation" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] FastAPI REST endpoints" \
  --body "GET /stocks, GET /reports, GET /reports/{id}" \
  --label "backend" --milestone "Phase 1 — MVP"
```

### Week 3 — Frontend + automation

```bash
gh issue create --title "[FEAT] React project setup (Vite + TS + Tailwind)" \
  --body "Vite + React 18 + TypeScript + TailwindCSS initial setup" \
  --label "frontend,setup" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] Ticker search + report viewer page" \
  --body "Connect to FastAPI via TanStack Query" \
  --label "frontend" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] Recharts report history chart" \
  --body "Time-series confidence_score by date" \
  --label "frontend" --milestone "Phase 1 — MVP"

gh issue create --title "[FEAT] GitHub Actions daily crawler automation" \
  --body "daily_crawler.yml with PostgreSQL service container" \
  --label "infra" --milestone "Phase 1 — MVP"
```

---

## Set GitHub Secrets

```bash
gh secret set OPENAI_API_KEY
gh secret set CRAWL_TICKERS   # e.g. AAPL,NVDA,005930,000660
```
