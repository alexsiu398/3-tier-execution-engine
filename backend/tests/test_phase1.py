"""
Phase 1 tests — RED first.

Tests cover:
- Health endpoint
- Config loads from env
- Database session factory (async)
- All ORM models can be created and persisted
- All Pydantic schemas validate correctly
- Test-case CRUD endpoints (create, list, get, update, delete)
- Settings CRUD endpoint (get + put)
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

# ── Env must be set before importing app ──────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STAGEHAND_MOCK", "true")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def app_client():
    """Spin up a fresh in-memory DB per test module."""
    from app.core.database import engine, Base
    from main import app

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Health check
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_returns_200(app_client):
    r = await app_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Config
# ─────────────────────────────────────────────────────────────────────────────

def test_settings_loads_database_url():
    from app.core.config import settings
    assert "sqlite" in settings.DATABASE_URL


def test_settings_stagehand_mock_flag():
    from app.core.config import settings
    assert settings.STAGEHAND_MOCK is True


# ─────────────────────────────────────────────────────────────────────────────
# 3. Database session
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_db_yields_async_session():
    from app.core.database import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    gen = get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    await gen.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# 4. ORM models — instantiation (no DB write needed for shape tests)
# ─────────────────────────────────────────────────────────────────────────────

def test_test_case_model_fields():
    from app.models.test_case import TestCase
    tc = TestCase(title="Demo", url="https://example.com", steps=[])
    assert tc.title == "Demo"
    assert tc.url == "https://example.com"
    assert tc.steps == []


def test_execution_model_fields():
    from app.models.execution import Execution
    ex = Execution(test_case_id=1, strategy="option_c", status="pending")
    assert ex.strategy == "option_c"
    assert ex.status == "pending"


def test_execution_step_model_fields():
    from app.models.execution import ExecutionStep
    step = ExecutionStep(
        execution_id=1,
        step_index=0,
        instruction="click the button",
        tier_used=1,
        success=True,
        duration_ms=42,
    )
    assert step.tier_used == 1
    assert step.success is True


def test_execution_settings_model_fields():
    from app.models.execution_settings import ExecutionSettings
    s = ExecutionSettings(
        fallback_strategy="option_c",
        timeout_per_tier_seconds=10,
        max_retry_per_tier=2,
    )
    assert s.fallback_strategy == "option_c"


def test_xpath_cache_model_fields():
    from app.models.xpath_cache import XPathCache
    xc = XPathCache(
        instruction_hash="abc123",
        url_pattern="https://example.com",
        xpath="//button[@id='submit']",
    )
    assert xc.instruction_hash == "abc123"
    assert xc.hit_count == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────

def test_test_step_schema_valid():
    from app.schemas.test_case import TestStepSchema
    s = TestStepSchema(action="click", instruction="click the submit button")
    assert s.action == "click"
    assert s.selector is None


def test_test_step_schema_invalid_action():
    from pydantic import ValidationError
    from app.schemas.test_case import TestStepSchema
    with pytest.raises(ValidationError):
        TestStepSchema(action="fly", instruction="do something impossible")


def test_test_case_create_schema():
    from app.schemas.test_case import TestCaseCreate
    from app.schemas.test_case import TestStepSchema
    tc = TestCaseCreate(
        title="My test",
        url="https://example.com",
        steps=[TestStepSchema(action="navigate", instruction="go home")],
    )
    assert len(tc.steps) == 1


def test_execution_settings_schema_defaults():
    from app.schemas.settings import ExecutionSettingsUpdate
    s = ExecutionSettingsUpdate()
    assert s.fallback_strategy == "option_c"
    assert s.timeout_per_tier_seconds == 10


# ─────────────────────────────────────────────────────────────────────────────
# 6. Test-case API endpoints
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_test_case(app_client):
    payload = {
        "title": "Homepage smoke",
        "url": "https://example.com",
        "steps": [
            {"action": "navigate", "instruction": "open the homepage"},
            {"action": "assert_text", "instruction": "check title text", "value": "Example"},
        ],
    }
    r = await app_client.post("/api/v1/tests", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["title"] == "Homepage smoke"
    assert len(data["steps"]) == 2


@pytest.mark.asyncio
async def test_list_test_cases(app_client):
    r = await app_client.get("/api/v1/tests")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_get_test_case_by_id(app_client):
    # Create one first
    payload = {"title": "Get test", "url": "https://example.com", "steps": []}
    create_r = await app_client.post("/api/v1/tests", json=payload)
    tc_id = create_r.json()["id"]

    r = await app_client.get(f"/api/v1/tests/{tc_id}")
    assert r.status_code == 200
    assert r.json()["id"] == tc_id


@pytest.mark.asyncio
async def test_get_test_case_not_found(app_client):
    r = await app_client.get("/api/v1/tests/99999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_test_case(app_client):
    payload = {"title": "Before update", "url": "https://example.com", "steps": []}
    create_r = await app_client.post("/api/v1/tests", json=payload)
    tc_id = create_r.json()["id"]

    update_payload = {"title": "After update", "url": "https://example.com", "steps": []}
    r = await app_client.put(f"/api/v1/tests/{tc_id}", json=update_payload)
    assert r.status_code == 200
    assert r.json()["title"] == "After update"


@pytest.mark.asyncio
async def test_delete_test_case(app_client):
    payload = {"title": "Delete me", "url": "https://example.com", "steps": []}
    create_r = await app_client.post("/api/v1/tests", json=payload)
    tc_id = create_r.json()["id"]

    r = await app_client.delete(f"/api/v1/tests/{tc_id}")
    assert r.status_code == 204

    r2 = await app_client.get(f"/api/v1/tests/{tc_id}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_create_test_case_invalid_step_action(app_client):
    payload = {
        "title": "Bad step",
        "url": "https://example.com",
        "steps": [{"action": "invalid_action", "instruction": "do something"}],
    }
    r = await app_client.post("/api/v1/tests", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_test_case_missing_title(app_client):
    r = await app_client.post("/api/v1/tests", json={"url": "https://example.com", "steps": []})
    assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 7. Settings endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_settings_returns_defaults(app_client):
    r = await app_client.get("/api/v1/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["fallback_strategy"] in ("option_a", "option_b", "option_c")


@pytest.mark.asyncio
async def test_put_settings_updates_strategy(app_client):
    r = await app_client.put(
        "/api/v1/settings",
        json={"fallback_strategy": "option_b", "timeout_per_tier_seconds": 15, "max_retry_per_tier": 1},
    )
    assert r.status_code == 200
    assert r.json()["fallback_strategy"] == "option_b"


@pytest.mark.asyncio
async def test_put_settings_invalid_strategy(app_client):
    r = await app_client.put(
        "/api/v1/settings",
        json={"fallback_strategy": "option_z"},
    )
    assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 8. Execution schemas
# ─────────────────────────────────────────────────────────────────────────────

def test_execution_step_response_schema():
    from app.schemas.execution import ExecutionStepResponse
    step = ExecutionStepResponse(
        id=1,
        step_index=0,
        instruction="click the button",
        tier_used=1,
        success=True,
        duration_ms=42.5,
        error=None,
        xpath_cached=False,
    )
    assert step.tier_used == 1
    assert step.xpath_cached is False


def test_execution_step_response_optional_fields():
    from app.schemas.execution import ExecutionStepResponse
    step = ExecutionStepResponse(
        id=2,
        step_index=1,
        instruction="assert title",
        tier_used=None,
        success=None,
        duration_ms=None,
        error="element not found",
        xpath_cached=True,
    )
    assert step.tier_used is None
    assert step.error == "element not found"
    assert step.xpath_cached is True


def test_execution_response_schema():
    from app.schemas.execution import ExecutionResponse
    ex = ExecutionResponse(
        id=1,
        test_case_id=2,
        strategy="option_c",
        status="completed",
        started_at=None,
        finished_at=None,
        steps=[],
    )
    assert ex.strategy == "option_c"
    assert ex.steps == []


# ─────────────────────────────────────────────────────────────────────────────
# 9. Settings idempotency — second GET after PUT should reflect update
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_settings_idempotent_after_update(app_client):
    await app_client.put(
        "/api/v1/settings",
        json={"fallback_strategy": "option_a", "timeout_per_tier_seconds": 5, "max_retry_per_tier": 1},
    )
    r = await app_client.get("/api/v1/settings")
    assert r.status_code == 200
    assert r.json()["fallback_strategy"] == "option_a"
    assert r.json()["timeout_per_tier_seconds"] == 5
