# Data Flow

End-to-end walkthrough of how a single piece of news becomes a scored investment report.

---

## Overview

```
[News Source] → [Crawler] → [DB: articles] → [Report Generator] → [DB: reports]
                                                                         │
                                                              [LLM Evaluator]
                                                                         │
                                                              [DB: evaluations]
                                                                         │
                                                              [FastAPI] → [Dashboard]
```

---

## Step 1 — News Collection

**Trigger:** GitHub Actions cron (`0 22 * * *` UTC = 07:00 KST)

**Sources:**

| Source | Method | Module |
|--------|--------|--------|
| Yahoo Finance RSS | `feedparser.parse(url)` | `crawler/collectors/yahoo.py` |
| Naver Finance | `requests` + `BeautifulSoup` | `crawler/collectors/naver.py` |

**Yahoo Finance RSS URL pattern:**
```
https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US
```

**Output per article (`RawArticle`):**
```python
ticker       # e.g. "AAPL"
title        # article headline
url          # original link
url_hash     # SHA-256(url) — dedup key
source       # "yahoo" | "naver"
published_at # datetime or None
content      # summary text from RSS / scraped body
```

---

## Step 2 — Deduplication & DB Upsert

**Module:** `crawler/main.py` (DB upsert logic in Phase 1)

**Deduplication strategy:**
- `url_hash = hashlib.sha256(url.encode()).hexdigest()`
- DB constraint: `UNIQUE(url_hash)` on the `articles` table
- Insert uses `ON CONFLICT DO NOTHING` — safe for re-runs and concurrent jobs

```
RawArticle
    │
    ├─ compute url_hash
    ├─ lookup stock_id from stocks table (by ticker)
    └─ INSERT INTO articles ... ON CONFLICT (url_hash) DO NOTHING
```

**articles table state after step 2:**
```
id | stock_id | title | source | url | url_hash | content | summary* | published_at
```
`summary` and `sentiment` are populated in a later enrichment pass (Phase 1).

---

## Step 3 — Report Generation

**Module:** `backend/app/services/report_generator.py`

**Input:** all `articles` for a given ticker from the past 24 hours

**Process:**
```
articles (content + title)
        │
        ▼
  system prompt (REPORT_SYSTEM_PROMPT)
  + user message (formatted article list)
        │
        ▼
  openai.beta.chat.completions.parse(
      model=settings.openai_model,
      response_format=ReportOutput      # Structured Output
  )
        │
        ▼
  ReportOutput (validated Pydantic model)
  ├── bull_points:       ["...", "..."]
  ├── bear_points:       ["...", "..."]
  ├── overall_summary:   "..."
  └── confidence_score:  0.0 – 1.0
        │
        ▼
  INSERT INTO reports (stock_id, report_date, bull_points, ...)
  UNIQUE(stock_id, report_date) → one report per ticker per day
```

**Why Structured Output over JSON mode:**
OpenAI Structured Output enforces the Pydantic schema at the API level, eliminating malformed JSON and missing fields without extra validation logic.

---

## Step 4 — Quality Evaluation

**Module:** `backend/app/ai/evaluator.py`

**Input:** a `Report` row just written to the DB

**Process:**
```
report (bull_points, bear_points, overall_summary, confidence_score)
        │
        ▼
  system prompt (EVAL_SYSTEM_PROMPT — judge role)
  + user message (formatted report)
        │
        ▼
  openai.chat.completions.create(model=...)
        │
        ▼
  parse response →
  ├── judge_score:    0.0 – 1.0
  └── judge_feedback: "..."
        │
        ▼
  INSERT INTO evaluations (report_id, judge_score, judge_feedback, model_used)
```

**Purpose:** Track how report quality changes as prompts evolve over time.
The `evaluations` table accumulates a time-series of scores per ticker,
making prompt regressions visible without manual review.

---

## Step 5 — API Layer

**Module:** `backend/app/api/v1/`

FastAPI reads from PostgreSQL via SQLAlchemy async sessions and returns JSON.
No write endpoints are exposed — all data is produced by the crawler/AI pipeline.

```
Client request
    │
    ▼
FastAPI router
    │
    ├─ GET /api/v1/stocks           → SELECT * FROM stocks ORDER BY ticker
    ├─ GET /api/v1/reports          → SELECT * FROM reports [WHERE stock_id=... AND report_date>=...]
    └─ GET /api/v1/reports/{id}     → SELECT * FROM reports WHERE id=...
    │
    ▼
AsyncSession.execute(select(...))
    │
    ▼
JSON response
```

---

## Step 6 — Dashboard

**Location:** `frontend/src/`

TanStack Query fetches from FastAPI via the Vite dev proxy (`/api` → `http://localhost:8000`).

```
App
├── Ticker search input
│       └── GET /api/v1/stocks → stock list
│
└── Report viewer (selected ticker)
        ├── GET /api/v1/reports?ticker=AAPL → report list
        │       └── renders bull/bear points + overall_summary
        │
        └── Recharts LineChart
                └── x: report_date, y: confidence_score (time-series)
```

---

## Daily Automation Timeline

```
06:55 KST  GitHub Actions job starts
07:00      Crawler: Yahoo Finance RSS + Naver Finance fetch
07:02      DB upsert (articles)
07:03      Report Generator: one OpenAI call per ticker
07:05      LLM Evaluator: one OpenAI call per report
07:06      Job complete — DB has fresh reports and evaluation scores
```

All steps are sequential within a single GitHub Actions job to simplify error handling and avoid partial state.

---

## Error & Edge Cases

| Scenario | Handling |
|----------|----------|
| Duplicate article URL | `ON CONFLICT DO NOTHING` — silently skipped |
| No new articles for ticker | Report Generator skips the ticker; no empty report written |
| OpenAI API error | Exception propagates; GitHub Actions marks step as failed; prior reports remain intact |
| DB connection failure | Alembic step fails early; crawler never runs |
| Unique report constraint violation | `UNIQUE(stock_id, report_date)` — re-run on same day skips insert |
