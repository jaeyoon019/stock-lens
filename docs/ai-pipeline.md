# AI Pipeline

Two-stage pipeline: **Report Generator** produces structured investment reports from raw news,
then **LLM Evaluator** scores each report automatically.

---

## Stage 1 — Report Generation

### Goal

Transform a list of raw news articles for a given ticker into a structured bull/bear report
with a confidence score, using a single OpenAI API call.

### Output Schema (`ReportOutput`)

```python
# backend/app/schemas/report.py
class ReportOutput(BaseModel):
    bull_points:       list[str]  # reasons to be bullish (3–5 items)
    bear_points:       list[str]  # reasons to be bearish (3–5 items)
    overall_summary:   str        # 2–3 sentence synthesis
    confidence_score:  float      # 0.0 (low conviction) – 1.0 (high conviction)
```

### Why Structured Output (not JSON mode)

| | JSON mode | Structured Output |
|-|-----------|-------------------|
| Schema enforcement | Prompt-level (best-effort) | API-level (guaranteed) |
| Validation needed | Yes — must handle malformed JSON | No — Pydantic model validated at parse |
| Field presence | Not guaranteed | Guaranteed |
| Cost | Same | Same |

`openai.beta.chat.completions.parse()` with `response_format=ReportOutput`
rejects the response at the API level if it doesn't match the schema,
so no defensive `try/except` parsing is needed in application code.

### Prompt Design

**System prompt role:** Equity research analyst.

Key constraints baked into the prompt:
- Extract only claims supported by the provided articles (no hallucination of external facts)
- `bull_points` and `bear_points` must each have 3–5 distinct items
- `confidence_score` reflects how much the articles actually move the investment thesis,
  not how positive the news is (a single speculative rumor → low score; multiple confirmed
  earnings beats → high score)

**User message format:**
```
Ticker: AAPL
Articles (24h):

[1] Title: Apple Reports Record Q3 Revenue
    Source: yahoo | Published: 2025-08-01
    Content: Apple Inc. reported ...

[2] Title: iPhone Supply Chain Concerns Rise
    Source: naver | Published: 2025-08-01
    Content: Analysts warn that ...

---
Generate a structured bull/bear report.
```

### API Call

```python
response = client.beta.chat.completions.parse(
    model=settings.openai_model,       # "gpt-4o-mini"
    messages=[
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ],
    response_format=ReportOutput,
)
report: ReportOutput = response.choices[0].message.parsed
```

### DB Write

```sql
INSERT INTO reports (stock_id, report_date, bull_points, bear_points,
                     overall_summary, confidence_score, article_count)
VALUES (...)
ON CONFLICT (stock_id, report_date) DO NOTHING;
-- one report per ticker per calendar day; re-runs are idempotent
```

---

## Stage 2 — LLM Evaluation (LLM-as-judge)

### Goal

Score every generated report on a 0.0–1.0 scale using a second, independent LLM call.
No human annotation required.

### Why LLM-as-judge

Manual review doesn't scale when running daily across multiple tickers.
A second LLM call acting as a "judge" provides a consistent, automated quality signal
that accumulates in the `evaluations` table over time, making prompt regressions visible.

### Evaluation Criteria

The judge prompt instructs the model to score along these dimensions:

| Dimension | Description |
|-----------|-------------|
| Grounding | Are bull/bear points traceable to the provided articles? |
| Specificity | Are claims specific (numbers, names, dates) or vague? |
| Balance | Does the report fairly represent both bull and bear cases? |
| Coherence | Does `overall_summary` logically follow from the points? |
| Score calibration | Is `confidence_score` appropriate given the evidence? |

### Output

```python
{
    "judge_score":    0.82,
    "judge_feedback": "Bull points are well-supported with specific revenue figures. "
                      "Bear section lacks specificity — 'supply chain concerns' should "
                      "cite the source article more precisely.",
    "model_used":     "gpt-4o-mini"
}
```

### API Call

```python
response = client.chat.completions.create(
    model=settings.openai_model,
    messages=[
        {"role": "system", "content": EVAL_SYSTEM_PROMPT},
        {"role": "user",   "content": format_report_for_eval(report)},
    ],
)
# parse judge_score and judge_feedback from response text
```

### DB Write

```sql
INSERT INTO evaluations (report_id, judge_score, judge_feedback, model_used)
VALUES (...);
-- multiple evaluations per report are allowed (e.g. re-evaluation after prompt change)
```

---

## Quality Tracking Over Time

The `evaluations` table is a time-series of judge scores per report.
Querying it reveals whether prompt changes improved or degraded output quality:

```sql
SELECT r.report_date, AVG(e.judge_score) AS avg_score
FROM evaluations e
JOIN reports r ON e.report_id = r.id
JOIN stocks s  ON r.stock_id  = s.id
WHERE s.ticker = 'AAPL'
GROUP BY r.report_date
ORDER BY r.report_date;
```

The React dashboard renders this as a `confidence_score` time-series chart (Recharts `LineChart`).

---

## Cost Model

All AI calls use `gpt-4o-mini`. Estimated per-run costs (10 tickers, ~5 articles each):

| Call | Input tokens | Output tokens | Cost/run | Cost/month |
|------|-------------|---------------|----------|------------|
| Report generation (×10) | ~2,000 | ~300 | ~$0.001 | ~$0.03 |
| LLM evaluation (×10) | ~800 | ~150 | ~$0.0005 | ~$0.015 |
| **Total** | | | **~$0.0015** | **~$0.045** |

Token counts scale linearly with article volume and ticker count.

---

## Prompt Iteration Workflow

```
1. Edit REPORT_SYSTEM_PROMPT or EVAL_SYSTEM_PROMPT in backend/app/ai/prompts.py
2. Run the pipeline manually:
       cd backend
       python -m app.services.report_generator
       python -m app.ai.evaluator
3. Query evaluations table — compare avg judge_score before and after
4. If score improved, commit the prompt change
```

This tight feedback loop (change → run → score → commit) is the core engineering
practice this project is designed to exercise.
