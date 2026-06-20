# GitHub 마일스톤 & 이슈 설정 가이드

## 사전 준비

```bash
# GitHub CLI 설치 확인
gh --version

# 로그인
gh auth login

# repo 생성 후 이동
gh repo create jaeyoon019/stock-lens --public --clone
cd stock-lens
```

---

## 라벨 생성

`gh label create`는 공식 지원됨.

```bash
gh label create "setup"      --color "BFD4F2" --description "초기 세팅"
gh label create "db"         --color "5319E7" --description "DB / 마이그레이션"
gh label create "crawler"    --color "0075CA" --description "데이터 수집"
gh label create "ai"         --color "E4E669" --description "AI / LLM"
gh label create "evaluation" --color "D93F0B" --description "평가 파이프라인"
gh label create "backend"    --color "0E8A16" --description "FastAPI / 서버"
gh label create "frontend"   --color "F9D0C4" --description "React / UI"
gh label create "infra"      --color "C5DEF5" --description "Docker / CI"
```

---

## 마일스톤 생성

`gh milestone create`는 공식 CLI에 없음. `gh api`로 생성한다.

```bash
gh api repos/:owner/:repo/milestones \
  --method POST \
  --field title="Phase 1 — MVP" \
  --field description="뉴스 수집 + AI 리포트 + 대시보드"

gh api repos/:owner/:repo/milestones \
  --method POST \
  --field title="Phase 2 — RAG" \
  --field description="벡터DB + 공시 분석"

gh api repos/:owner/:repo/milestones \
  --method POST \
  --field title="Phase 3 — Agent" \
  --field description="LangGraph 멀티에이전트 + 챗봇"
```

마일스톤 번호 확인:
```bash
gh api repos/:owner/:repo/milestones --jq '.[] | {number, title}'
```

---

## Phase 1 이슈 생성

아래 실행 전 `--milestone` 번호를 `gh api`로 확인한 값으로 교체할 것.

### Week 1 — 데이터 수집 + DB

```bash
gh issue create --title "[FEAT] Docker Compose PostgreSQL 세팅" \
  --body "docker-compose.yml 작성, healthcheck 포함" \
  --label "setup,infra" --milestone 1

gh issue create --title "[FEAT] SQLAlchemy 모델 정의 (4개 테이블)" \
  --body "stocks, articles, reports, evaluations" \
  --label "db" --milestone 1

gh issue create --title "[FEAT] Alembic 초기 마이그레이션" \
  --body "alembic init + 첫 revision 생성" \
  --label "db" --milestone 1

gh issue create --title "[FEAT] Yahoo Finance RSS 크롤러" \
  --body "feedparser 기반, url_hash 중복 제거" \
  --label "crawler" --milestone 1

gh issue create --title "[FEAT] 네이버 금융 크롤러" \
  --body "requests + BeautifulSoup 기반" \
  --label "crawler" --milestone 1

gh issue create --title "[FEAT] DB upsert 로직 (article 중복 방지)" \
  --body "url_hash 기반 ON CONFLICT DO NOTHING" \
  --label "crawler,db" --milestone 1
```

### Week 2 — AI 파이프라인

```bash
gh issue create --title "[FEAT] OpenAI Structured Output 리포트 생성기" \
  --body "bull_points, bear_points, overall_summary, confidence_score" \
  --label "ai" --milestone 1

gh issue create --title "[FEAT] Pydantic v2 리포트 스키마 정의" \
  --body "ReportOutput 모델, JSON mode" \
  --label "ai" --milestone 1

gh issue create --title "[FEAT] LLM-as-judge 평가 파이프라인" \
  --body "생성된 리포트를 2차 LLM 호출로 0.0-1.0 점수 부여" \
  --label "ai,evaluation" --milestone 1

gh issue create --title "[FEAT] FastAPI REST 엔드포인트" \
  --body "GET /stocks, GET /reports, GET /reports/{id}" \
  --label "backend" --milestone 1
```

### Week 3 — 프론트엔드 + 자동화

```bash
gh issue create --title "[FEAT] React 프로젝트 세팅 (Vite + TS + Tailwind)" \
  --label "frontend,setup" --milestone 1

gh issue create --title "[FEAT] 종목 검색 + 리포트 뷰어 페이지" \
  --body "TanStack Query로 FastAPI 연동" \
  --label "frontend" --milestone 1

gh issue create --title "[FEAT] Recharts 리포트 히스토리 차트" \
  --body "날짜별 confidence_score 시계열" \
  --label "frontend" --milestone 1

gh issue create --title "[FEAT] GitHub Actions 일일 자동 크롤링" \
  --body "daily_crawler.yml, PostgreSQL service container 포함" \
  --label "infra" --milestone 1
```

---

## GitHub Secrets 설정

```bash
gh secret set OPENAI_API_KEY
gh secret set CRAWL_TICKERS   # 예: AAPL,NVDA,005930,000660
```
