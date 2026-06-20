# API Reference

Base URL: `http://localhost:8000`

All endpoints return JSON. No authentication required (personal project).

---

## Health Check

### `GET /health`

Confirms the server is running.

**Response `200`**
```json
{ "status": "ok" }
```

---

## Stocks

### `GET /api/v1/stocks`

Returns all tracked tickers, ordered alphabetically.

**Response `200`** — array of Stock objects
```json
[
  {
    "id":         "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "ticker":     "AAPL",
    "name":       "Apple Inc.",
    "market":     "NASDAQ",
    "sector":     "Technology",
    "created_at": "2025-08-01T00:00:00",
    "updated_at": "2025-08-01T00:00:00"
  },
  ...
]
```

**Empty state** (no tickers seeded yet): `[]`

---

### `GET /api/v1/stocks/{ticker}`

Returns a single stock by ticker symbol (case-insensitive).

**Path parameter**

| Name | Type | Example |
|------|------|---------|
| `ticker` | string | `AAPL`, `005930` |

**Response `200`**
```json
{
  "id":         "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "ticker":     "AAPL",
  "name":       "Apple Inc.",
  "market":     "NASDAQ",
  "sector":     "Technology",
  "created_at": "2025-08-01T00:00:00",
  "updated_at": "2025-08-01T00:00:00"
}
```

**Response `404`**
```json
{ "detail": "Stock not found" }
```

---

## Reports

### `GET /api/v1/reports`

Returns all reports, newest first. Supports optional filtering.

**Query parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `ticker` | string | No | Filter by ticker symbol |
| `from_date` | date (`YYYY-MM-DD`) | No | Return reports on or after this date |

**Example requests**
```
GET /api/v1/reports
GET /api/v1/reports?ticker=AAPL
GET /api/v1/reports?ticker=NVDA&from_date=2025-08-01
```

**Response `200`** — array of Report objects
```json
[
  {
    "id":               "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "stock_id":         "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "report_date":      "2025-08-01",
    "bull_points": [
      "Record Q3 revenue of $85.8B, up 5% YoY, beating analyst estimates.",
      "Services segment grew 14% YoY, expanding high-margin recurring revenue.",
      "iPhone 16 pre-orders tracking above iPhone 15 at the same stage."
    ],
    "bear_points": [
      "China revenue declined 6% YoY amid intensifying local competition.",
      "Gross margin guidance of 45.5–46.5% is below last quarter's 46.3%.",
      "Ongoing EU regulatory pressure on App Store could reduce services growth."
    ],
    "overall_summary":  "Apple delivered a solid quarter driven by Services, but China headwinds and margin compression warrant caution. Overall thesis remains intact with moderate conviction.",
    "confidence_score": 0.74,
    "article_count":    8,
    "created_at":       "2025-08-01T07:05:32"
  },
  ...
]
```

---

### `GET /api/v1/reports/{report_id}`

Returns a single report by UUID.

**Path parameter**

| Name | Type | Example |
|------|------|---------|
| `report_id` | UUID string | `7c9e6679-7425-40de-944b-e07fc1f90ae7` |

**Response `200`** — single Report object (same schema as above)

**Response `404`**
```json
{ "detail": "Report not found" }
```

---

## Data Models

### Stock

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `ticker` | string | Ticker symbol (e.g. `AAPL`, `005930`) |
| `name` | string | Company name |
| `market` | string | `NASDAQ` \| `NYSE` \| `KRX` |
| `sector` | string \| null | Industry sector |
| `created_at` | datetime | Row creation time |
| `updated_at` | datetime | Last update time |

### Report

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `stock_id` | UUID | FK → stocks.id |
| `report_date` | date | Calendar date of the report |
| `bull_points` | string[] | Bullish arguments (3–5 items) |
| `bear_points` | string[] | Bearish arguments (3–5 items) |
| `overall_summary` | string | 2–3 sentence synthesis |
| `confidence_score` | float | 0.0–1.0 conviction score |
| `article_count` | integer | Number of articles used |
| `created_at` | datetime | Row creation time |

---

## Interactive Docs

FastAPI auto-generates interactive API documentation:

| UI | URL |
|----|-----|
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |

---

## Planned Endpoints (Phase 1)

The following endpoints are planned but not yet implemented:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/reports/{id}/evaluation` | Fetch evaluation scores for a report |
| `GET` | `/api/v1/stocks/{ticker}/reports` | All reports for a specific ticker |
| `GET` | `/api/v1/stocks/{ticker}/articles` | Recent articles for a specific ticker |
