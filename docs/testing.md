# Testing

## Overview

Tests live in `backend/tests/`. The suite uses a **real database connection** — no mocks.
This matches production behaviour and catches issues that mocked tests would miss.

---

## Prerequisites

Before running tests, ensure the `stocklens` database is running and accessible.

**With Docker Compose (recommended):**
```bash
docker compose up -d db
```

**Without Docker (local PostgreSQL):**
```bash
psql -U postgres -c "CREATE DATABASE stocklens_test;"
```

Set `DATABASE_URL` to point at the test database:
```bash
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stocklens
```

---

## Running tests

```bash
cd backend

# Run all tests
pytest

# Run with output
pytest -v

# Run a specific file
pytest tests/test_reports.py

# Run a specific test
pytest tests/test_reports.py::test_get_report_not_found
```

---

## Test structure

```
backend/tests/
├── __init__.py
├── conftest.py          # shared fixtures (DB session, test client)
├── test_stocks.py       # GET /api/v1/stocks
└── test_reports.py      # GET /api/v1/reports, GET /api/v1/reports/{id}
```

---

## Writing tests

### Fixtures (`conftest.py`)

The test suite needs two shared fixtures:

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

engine = create_async_engine(settings.database_url)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

### Example test

```python
import pytest

@pytest.mark.asyncio
async def test_get_report_invalid_uuid(client):
    response = await client.get("/api/v1/reports/not-a-uuid")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_report_not_found(client):
    response = await client.get("/api/v1/reports/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"
```

---

## Test dependencies

Add these to `backend/requirements.txt` (or a separate `requirements-dev.txt`):

```
pytest
pytest-asyncio
httpx
```

---

## Rules

- **Never mock the database.** Tests must hit a real PostgreSQL instance.
- **Never run the AI pipeline (OpenAI calls) in tests.** Mock the `openai` client or skip those tests.
- **Each test gets a clean DB.** The `reset_db` fixture drops and recreates all tables before every test.
- **Do not run tests in CI against the production DB.** The GitHub Actions workflow runs a separate PostgreSQL service container for this purpose.

---

## CI behaviour

Tests are not yet wired into the GitHub Actions workflow. When added, the step should run
after `alembic upgrade head` and use the same service container PostgreSQL instance:

```yaml
- name: Run tests
  working-directory: backend
  run: pytest -v
```
