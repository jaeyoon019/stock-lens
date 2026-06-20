# 📈 stock-lens

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
- Multi-source news crawling with deduplication (Yahoo Finance RSS, 네이버 금융)
- Structured AI report generation (bull/bear points, confidence score) via OpenAI Structured Output
- LLM-as-judge evaluation pipeline to track report quality over time
- Daily automation via GitHub Actions
- React dashboard with ticker search and report history

---

## Architecture

```
News Sources (Yahoo Finance RSS, 네이버 금융)
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
│   │   ├── api/v1/          # FastAPI routers (stocks, articles, reports)
│   │   ├── core/            # config.py, database.py
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic v2 request/response schemas
│   │   ├── services/        # report_generator.py, crawler_service.py
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
│       ├── services/        # api.ts
│       └── types/
├── docs/
│   └── architecture/
│       └── erd.mmd          # Mermaid ERD
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│       └── daily_crawler.yml
├── docker-compose.yml
└── README.md
```

---

## Database Schema

Full ERD: [`docs/architecture/erd.mmd`](docs/architecture/erd.mmd) (render at [mermaid.live](https://mermaid.live))

| Table         | Description                                          |
|---------------|------------------------------------------------------|
| `stocks`      | 종목 메타데이터 (ticker, name, market, sector)         |
| `articles`    | 크롤링된 뉴스 (url_hash로 중복 제거, AI 요약 포함)      |
| `reports`     | 종목별 일일 bull/bear 리포트 + confidence_score        |
| `evaluations` | LLM-as-judge 점수 및 피드백 (0.0–1.0)                |

---

## Environment Variables

`.env.example` 참고. 실제 `.env`는 절대 커밋하지 않는다.

| Variable           | Description                  | Example                              |
|--------------------|------------------------------|--------------------------------------|
| `DATABASE_URL`     | PostgreSQL 연결 문자열          | `postgresql+asyncpg://user:pw@db/stocklens` |
| `OPENAI_API_KEY`   | OpenAI API 키                 | `sk-...`                             |
| `OPENAI_MODEL`     | 사용할 모델                    | `gpt-4o-mini`                        |
| `CRAWL_TICKERS`    | 크롤링 대상 종목 (쉼표 구분)      | `AAPL,005930,NVDA`                   |
| `LOG_LEVEL`        | 로그 레벨                      | `INFO`                               |

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
# .env에 OPENAI_API_KEY, CRAWL_TICKERS 입력
```

### 2. Start services

```bash
docker compose up -d
```

이것만으로 PostgreSQL + FastAPI + 마이그레이션이 모두 실행된다.

### 3. Frontend (개발 모드)

```bash
cd frontend
npm install
npm run dev
```

`http://localhost:5173` 에서 대시보드 확인.

### 4. Run crawler manually

```bash
docker compose exec backend python -m crawler.main
```

---

## OpenAI Cost Estimate

| 항목             | 모델         | 예상 토큰/일  | 예상 비용/월  |
|------------------|-------------|-------------|-------------|
| 뉴스 요약         | gpt-4o-mini | ~50k tokens | ~$0.03      |
| 리포트 생성       | gpt-4o-mini | ~30k tokens | ~$0.02      |
| LLM 평가         | gpt-4o-mini | ~20k tokens | ~$0.01      |
| **합계**         |             |             | **~$0.06/월** |

종목 수와 뉴스 수에 따라 변동. 10개 종목 기준 추정치.

---

## Data Sources & Policy

| 소스               | 방식              | 크롤링 주기 | 비고                  |
|--------------------|-----------------|----------|----------------------|
| Yahoo Finance RSS  | RSS 파싱          | 매일 07:00 KST | robots.txt 준수       |
| 네이버 금융         | HTML 파싱 (requests) | 매일 07:00 KST | 과도한 요청 자제, 1s 딜레이 |

개인 학습 목적의 프로젝트. 수집 데이터는 외부에 재배포하지 않는다.

---

## Evaluation Framework

```python
# 모든 생성 리포트는 자동으로 평가됨
{
  "judge_score": 0.82,   # 0.0 – 1.0
  "judge_feedback": "Bull points well-supported. Bear section lacks specificity.",
  "model_used": "gpt-4o-mini"
}
```

`evaluations` 테이블에 누적 저장되어 프롬프트 개선 효과를 시계열로 추적할 수 있다.

---

## Roadmap

- [x] Phase 0 — 프로젝트 설계 및 문서화
- [ ] Phase 1 — MVP: 뉴스 수집 + AI 리포트 + 대시보드 (Week 1–3)
- [ ] Phase 2 — RAG: 벡터DB + 공시 분석 (Week 4–7)
- [ ] Phase 3 — Agent: LangGraph 멀티에이전트 + 챗봇 (Week 8+)

---

## License

MIT
