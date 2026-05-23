"""
Phase 3 tests — REST API Layer (RED → GREEN TDD).

Tests cover:
POST /api/v1/executions         — create execution, start background task
GET  /api/v1/executions         — history list with aggregated tier stats
GET  /api/v1/executions/{id}    — detail with all steps
GET  /api/v1/executions/{id}/stream — SSE stream (live queue + completed-from-DB)

Edge cases:
- Test case not found → 404
- Execution not found → 404
- SSE for completed execution returns steps from DB
- SSE for in-flight execution drains live queue
- Default strategy taken from settings when not provided
- Explicit strategy overrides settings
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STAGEHAND_MOCK", "true")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(autouse=True)
async def clear_execution_queues():
    """Prevent _execution_queues state from leaking between tests.

    SQLite resets auto-increment IDs when tables are dropped/recreated per test,
    so a later test can get the same execution_id as an earlier one.  If the
    earlier test mocked _run_execution_bg (never putting a sentinel on the queue),
    the SSE handler for the later test would find the stale queue and block
    for 30 s.  Clearing the dict before and after each test prevents this.
    """
    from app.api.executions import _execution_queues
    _execution_queues.clear()
    yield
    _execution_queues.clear()


@pytest_asyncio.fixture
async def app_and_db():
    """Fresh in-memory DB + ASGI client per test."""
    from app.core.database import Base, engine
    from main import app

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield app, client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(app_and_db):
    _, c = app_and_db
    yield c


@pytest_asyncio.fixture
async def seeded_test_case(client):
    """Create and return a test case for use in execution tests."""
    payload = {
        "title": "Phase3 smoke",
        "url": "https://example.com",
        "steps": [
            {"action": "navigate", "instruction": "open the homepage", "value": "https://example.com"},
            {"action": "assert_text", "instruction": "check title", "selector": "h1", "value": "Example"},
        ],
    }
    r = await client.post("/api/v1/tests", json=payload)
    assert r.status_code == 201
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Helper: insert a completed execution + steps into the DB directly
# ─────────────────────────────────────────────────────────────────────────────


async def _seed_completed_execution(db: AsyncSession, test_case_id: int, strategy: str = "option_a"):
    """Insert a completed Execution with 2 ExecutionStep rows and return it."""
    from app.models.execution import Execution, ExecutionStep

    exe = Execution(
        test_case_id=test_case_id,
        strategy=strategy,
        status="completed",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(exe)
    await db.flush()

    steps = [
        ExecutionStep(
            execution_id=exe.id,
            step_index=0,
            instruction="open the homepage",
            tier_used=1,
            success=True,
            duration_ms=48.0,
            xpath_cached=False,
        ),
        ExecutionStep(
            execution_id=exe.id,
            step_index=1,
            instruction="check title",
            tier_used=2,
            success=True,
            duration_ms=120.0,
            xpath_cached=True,
        ),
    ]
    for s in steps:
        db.add(s)
    await db.commit()
    await db.refresh(exe)
    return exe


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /api/v1/executions
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_execution_returns_202(client, seeded_test_case):
    """POST should return 202 Accepted with an execution_id."""
    with patch("app.api.executions._run_execution_bg", new_callable=AsyncMock):
        r = await client.post(
            "/api/v1/executions",
            json={"test_case_id": seeded_test_case["id"]},
        )
        await asyncio.sleep(0)  # let the noop task complete
    assert r.status_code == 202
    data = r.json()
    assert "execution_id" in data
    assert isinstance(data["execution_id"], int)
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_execution_persists_to_db(client, seeded_test_case):
    """Execution row should be written to DB immediately."""
    from app.core.database import AsyncSessionLocal
    from app.models.execution import Execution

    with patch("app.api.executions._run_execution_bg", new_callable=AsyncMock):
        r = await client.post(
            "/api/v1/executions",
            json={"test_case_id": seeded_test_case["id"], "strategy": "option_b"},
        )
        await asyncio.sleep(0)
    assert r.status_code == 202
    execution_id = r.json()["execution_id"]

    async with AsyncSessionLocal() as db:
        exe = await db.get(Execution, execution_id)
        assert exe is not None
        assert exe.strategy == "option_b"
        assert exe.status == "pending"
        assert exe.test_case_id == seeded_test_case["id"]


@pytest.mark.asyncio
async def test_create_execution_uses_settings_strategy(client, seeded_test_case):
    """When strategy is omitted, the settings fallback_strategy should be used."""
    from app.core.database import AsyncSessionLocal
    from app.models.execution import Execution

    # Set strategy to option_a in settings
    await client.put(
        "/api/v1/settings",
        json={"fallback_strategy": "option_a", "timeout_per_tier_seconds": 10, "max_retry_per_tier": 2},
    )

    with patch("app.api.executions._run_execution_bg", new_callable=AsyncMock):
        r = await client.post(
            "/api/v1/executions",
            json={"test_case_id": seeded_test_case["id"]},
        )
        await asyncio.sleep(0)
    assert r.status_code == 202

    async with AsyncSessionLocal() as db:
        exe = await db.get(Execution, r.json()["execution_id"])
        assert exe.strategy == "option_a"


@pytest.mark.asyncio
async def test_create_execution_explicit_strategy_overrides_settings(client, seeded_test_case):
    """An explicitly provided strategy takes precedence over settings."""
    from app.core.database import AsyncSessionLocal
    from app.models.execution import Execution

    await client.put(
        "/api/v1/settings",
        json={"fallback_strategy": "option_a", "timeout_per_tier_seconds": 10, "max_retry_per_tier": 2},
    )

    with patch("app.api.executions._run_execution_bg", new_callable=AsyncMock):
        r = await client.post(
            "/api/v1/executions",
            json={"test_case_id": seeded_test_case["id"], "strategy": "option_c"},
        )
        await asyncio.sleep(0)

    async with AsyncSessionLocal() as db:
        exe = await db.get(Execution, r.json()["execution_id"])
        assert exe.strategy == "option_c"


@pytest.mark.asyncio
async def test_create_execution_invalid_test_case_returns_404(client):
    """Referencing a non-existent test case should return 404."""
    r = await client.post("/api/v1/executions", json={"test_case_id": 99999})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_execution_invalid_strategy_returns_422(client, seeded_test_case):
    """Invalid strategy value should return 422 Unprocessable Entity."""
    r = await client.post(
        "/api/v1/executions",
        json={"test_case_id": seeded_test_case["id"], "strategy": "option_z"},
    )
    assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 2. GET /api/v1/executions  (history list)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_executions_empty(client):
    """When there are no executions, the list endpoint returns []."""
    r = await client.get("/api/v1/executions")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_executions_returns_items(client, seeded_test_case):
    """After creating executions, they appear in the list."""
    with patch("app.api.executions._run_execution_bg", new_callable=AsyncMock):
        await client.post("/api/v1/executions", json={"test_case_id": seeded_test_case["id"]})
        await client.post("/api/v1/executions", json={"test_case_id": seeded_test_case["id"]})
        await asyncio.sleep(0)

    r = await client.get("/api/v1/executions")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_list_executions_aggregated_stats(client, seeded_test_case):
    """Aggregated tier stats must be included for completed executions."""
    from app.core.database import AsyncSessionLocal

    tc_id = seeded_test_case["id"]
    async with AsyncSessionLocal() as db:
        await _seed_completed_execution(db, tc_id, strategy="option_a")

    r = await client.get("/api/v1/executions")
    assert r.status_code == 200
    items = r.json()

    completed = next((i for i in items if i["status"] == "completed"), None)
    assert completed is not None
    assert completed["total_steps"] == 2
    assert completed["tier1_count"] == 1
    assert completed["tier2_count"] == 1
    assert completed["tier3_count"] == 0
    assert completed["success_count"] == 2


@pytest.mark.asyncio
async def test_list_executions_response_fields(client, seeded_test_case):
    """Each list item must contain all required fields."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await _seed_completed_execution(db, seeded_test_case["id"])

    r = await client.get("/api/v1/executions")
    item = r.json()[0]
    required_fields = {
        "id", "test_case_id", "strategy", "status",
        "started_at", "finished_at",
        "total_steps", "tier1_count", "tier2_count", "tier3_count", "success_count",
    }
    assert required_fields.issubset(item.keys())


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET /api/v1/executions/{id}  (detail)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_execution_detail_returns_steps(client, seeded_test_case):
    """Execution detail should include all ExecutionStep rows."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        exe = await _seed_completed_execution(db, seeded_test_case["id"])
        exe_id = exe.id

    r = await client.get(f"/api/v1/executions/{exe_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == exe_id
    assert data["status"] == "completed"
    assert len(data["steps"]) == 2


@pytest.mark.asyncio
async def test_get_execution_detail_step_fields(client, seeded_test_case):
    """Step responses include all expected fields."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        exe = await _seed_completed_execution(db, seeded_test_case["id"])
        exe_id = exe.id

    r = await client.get(f"/api/v1/executions/{exe_id}")
    step = r.json()["steps"][0]
    expected = {"id", "step_index", "instruction", "tier_used", "success", "duration_ms", "error", "xpath_cached"}
    assert expected.issubset(step.keys())
    assert step["step_index"] == 0
    assert step["tier_used"] == 1
    assert step["success"] is True
    assert step["xpath_cached"] is False


@pytest.mark.asyncio
async def test_get_execution_detail_not_found(client):
    """Non-existent execution ID should return 404."""
    r = await client.get("/api/v1/executions/99999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_execution_detail_correct_strategy(client, seeded_test_case):
    """Strategy field in detail response must match what was stored."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        exe = await _seed_completed_execution(db, seeded_test_case["id"], strategy="option_c")
        exe_id = exe.id

    r = await client.get(f"/api/v1/executions/{exe_id}")
    assert r.json()["strategy"] == "option_c"


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET /api/v1/executions/{id}/stream  (SSE)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sse_stream_completed_execution_returns_db_steps(client, seeded_test_case):
    """For a completed execution (no live queue), SSE replays steps from DB."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        exe = await _seed_completed_execution(db, seeded_test_case["id"])
        exe_id = exe.id

    async with client.stream("GET", f"/api/v1/executions/{exe_id}/stream") as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        events = []
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                events.append(event)
                if event.get("type") == "done":
                    break

    step_events = [e for e in events if "tier" in e]
    assert len(step_events) == 2
    assert step_events[0]["step_index"] == 0
    assert step_events[0]["tier"] == 1
    assert step_events[1]["step_index"] == 1
    assert step_events[1]["tier"] == 2
    assert step_events[1]["xpath_cached"] is True

    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_sse_stream_not_found(client):
    """Streaming a non-existent execution should return 404."""
    r = await client.get("/api/v1/executions/99999/stream")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_sse_stream_live_queue_delivers_events(client, seeded_test_case):
    """For an in-flight execution, SSE delivers events from the live asyncio.Queue."""
    from app.core.database import AsyncSessionLocal
    from app.models.execution import Execution
    from app.api.executions import _execution_queues

    tc_id = seeded_test_case["id"]

    # Create a running execution in DB
    async with AsyncSessionLocal() as db:
        exe = Execution(test_case_id=tc_id, strategy="option_c", status="running",
                        started_at=datetime.now(timezone.utc))
        db.add(exe)
        await db.commit()
        await db.refresh(exe)
        exe_id = exe.id

    # Pre-populate the queue with events + sentinel
    queue: asyncio.Queue = asyncio.Queue()
    _execution_queues[exe_id] = queue
    await queue.put({"step_index": 0, "tier": 1, "success": True, "duration_ms": 50.0, "xpath_cached": False})
    await queue.put({"step_index": 1, "tier": 3, "success": True, "duration_ms": 2000.0, "xpath_cached": False})
    await queue.put(None)  # sentinel — ends the stream

    try:
        async with client.stream("GET", f"/api/v1/executions/{exe_id}/stream") as r:
            assert r.status_code == 200
            events = []
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    events.append(event)
                    if event.get("type") == "done":
                        break
    finally:
        _execution_queues.pop(exe_id, None)

    step_events = [e for e in events if "tier" in e]
    assert len(step_events) == 2
    assert step_events[0]["tier"] == 1
    assert step_events[1]["tier"] == 3

    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_sse_stream_live_queue_cleaned_up_after_stream(client, seeded_test_case):
    """The queue should be removed from _execution_queues after streaming completes."""
    from app.core.database import AsyncSessionLocal
    from app.models.execution import Execution
    from app.api.executions import _execution_queues

    tc_id = seeded_test_case["id"]

    async with AsyncSessionLocal() as db:
        exe = Execution(test_case_id=tc_id, strategy="option_a", status="running",
                        started_at=datetime.now(timezone.utc))
        db.add(exe)
        await db.commit()
        await db.refresh(exe)
        exe_id = exe.id

    queue: asyncio.Queue = asyncio.Queue()
    _execution_queues[exe_id] = queue
    await queue.put(None)  # immediately done

    async with client.stream("GET", f"/api/v1/executions/{exe_id}/stream") as r:
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event.get("type") == "done":
                    break

    # Queue should have been removed
    assert exe_id not in _execution_queues


# ─────────────────────────────────────────────────────────────────────────────
# BUG FIX: xpath in step payload must survive save → load → execute
# When a client submits a step with "xpath" instead of "selector", the value
# must be stored under "selector" in the DB so that _run_execution_bg can
# construct Step(**row) without a TypeError crash and Tier 1 can use it.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_step_xpath_stored_as_selector_in_db(client):
    """xpath submitted via API is persisted as selector, not as a separate key."""
    payload = {
        "title": "XPath step test",
        "url": "https://example.com",
        "steps": [
            {
                "action": "click",
                "instruction": "click the submit button",
                "xpath": "//button[@id='submit']",
            }
        ],
    }
    r = await client.post("/api/v1/tests", json=payload)
    assert r.status_code == 201
    data = r.json()
    step = data["steps"][0]
    # selector must be populated from xpath
    assert step["selector"] == "//button[@id='submit']"
    # xpath must NOT be stored as a separate field (would crash Step(**row) later)
    assert "xpath" not in step


@pytest.mark.asyncio
async def test_step_with_xpath_does_not_crash_execution_bg(client):
    """Starting an execution whose steps were saved with xpath must not crash."""
    from app.core.database import AsyncSessionLocal
    from app.models.test_case import TestCase

    # Simulate a test case that was saved before the fix — has "xpath" key in JSON
    async with AsyncSessionLocal() as db:
        tc = TestCase(
            title="Legacy xpath step",
            url="https://example.com",
            steps=[
                {
                    "action": "click",
                    "instruction": "click submit",
                    "xpath": "//button[@id='submit']",
                    "selector": None,
                    "value": None,
                }
            ],
        )
        db.add(tc)
        await db.commit()
        await db.refresh(tc)
        tc_id = tc.id

    # _run_execution_bg must not raise TypeError when constructing Step(**row)
    from app.api.executions import _run_execution_bg
    from app.models.test_case import TestCase as TC

    async with AsyncSessionLocal() as db:
        tc_db = await db.get(TC, tc_id)
        steps_data = list(tc_db.steps)

    from app.api.executions import _normalize_step_data
    from app.services.models import Step

    # This is the exact construction in _run_execution_bg — must not raise.
    steps = [Step(**_normalize_step_data(s)) for s in steps_data]
    # Legacy record had selector=None but xpath set — selector must be populated
    assert steps[0].selector == "//button[@id='submit']"


def test_normalize_step_data_recovers_xpath_marker_format():
    from app.api.executions import _normalize_step_data

    normalized = _normalize_step_data(
        {
            "action": "fill",
            "instruction": 'input username with "standard_user"',
            "selector": "XPath",
            "value": "//input[@id='user-name']",
        }
    )

    assert normalized["selector"] == "//input[@id='user-name']"
    assert normalized["value"] == "standard_user"


def test_normalize_step_data_recovers_xpath_marker_for_click():
    from app.api.executions import _normalize_step_data

    normalized = _normalize_step_data(
        {
            "action": "click",
            "instruction": "login",
            "selector": "XPath",
            "value": "//input[@id='login-button']",
        }
    )

    assert normalized["selector"] == "//input[@id='login-button']"


# ─────────────────────────────────────────────────────────────────────────────
# 5. _run_execution_bg — background task logic (unit test without real browser)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_execution_bg_updates_status_to_completed():
    """Background task should update execution to 'running' then 'completed'."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from app.core.database import Base
    from app.models.execution import Execution
    from app.models.test_case import TestCase
    from app.api.executions import _run_execution_bg

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        tc = TestCase(title="T", url="https://example.com",
                      steps=[{"action": "navigate", "instruction": "go", "value": "https://example.com", "selector": None}])
        db.add(tc)
        await db.flush()

        exe = Execution(test_case_id=tc.id, strategy="option_a", status="pending")
        db.add(exe)
        await db.commit()
        exe_id = exe.id
        steps_data = tc.steps
        base_url = tc.url

    queue: asyncio.Queue = asyncio.Queue()

    # Mock Playwright so we don't need a real browser
    mock_page = MagicMock()
    mock_page.url = "https://example.com"
    mock_page.goto = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = AsyncMock()
    mock_pw.chromium = mock_chromium
    mock_pw.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.executions.AsyncSessionLocal", factory), \
         patch("app.api.executions.async_playwright", return_value=mock_pw):
        await _run_execution_bg(exe_id, steps_data, base_url, "option_a", 10, queue)

    async with factory() as db:
        exe = await db.get(Execution, exe_id)
        assert exe.status == "completed"
        assert exe.started_at is not None
        assert exe.finished_at is not None


@pytest.mark.asyncio
async def test_run_execution_bg_puts_sentinel_on_queue():
    """Background task must always put None sentinel on the queue when done."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from app.core.database import Base
    from app.models.execution import Execution
    from app.models.test_case import TestCase
    from app.api.executions import _run_execution_bg

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        tc = TestCase(title="T", url="https://example.com",
                      steps=[{"action": "navigate", "instruction": "go", "value": "https://example.com", "selector": None}])
        db.add(tc)
        await db.flush()
        exe = Execution(test_case_id=tc.id, strategy="option_c", status="pending")
        db.add(exe)
        await db.commit()
        exe_id = exe.id
        steps_data = tc.steps
        base_url = tc.url

    queue: asyncio.Queue = asyncio.Queue()

    mock_page = MagicMock()
    mock_page.url = "https://example.com"
    mock_page.goto = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = AsyncMock()
    mock_pw.chromium = mock_chromium
    mock_pw.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.executions.AsyncSessionLocal", factory), \
         patch("app.api.executions.async_playwright", return_value=mock_pw):
        await _run_execution_bg(exe_id, steps_data, base_url, "option_c", 10, queue)

    # Drain queue — last item must be None
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    assert items[-1] is None, "Sentinel (None) must be last item in queue"


@pytest.mark.asyncio
async def test_run_execution_bg_puts_events_on_queue():
    """Each executed step should emit an event dict on the queue."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from app.core.database import Base
    from app.models.execution import Execution
    from app.models.test_case import TestCase
    from app.api.executions import _run_execution_bg

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        tc = TestCase(
            title="T",
            url="https://example.com",
            steps=[
                {"action": "navigate", "instruction": "go home", "value": "https://example.com", "selector": None},
                {"action": "navigate", "instruction": "go docs", "value": "https://docs.example.com", "selector": None},
            ],
        )
        db.add(tc)
        await db.flush()
        exe = Execution(test_case_id=tc.id, strategy="option_a", status="pending")
        db.add(exe)
        await db.commit()
        exe_id = exe.id
        steps_data = tc.steps[:]
        base_url = tc.url

    queue: asyncio.Queue = asyncio.Queue()

    mock_page = MagicMock()
    mock_page.url = "https://example.com"
    mock_page.goto = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = AsyncMock()
    mock_pw.chromium = mock_chromium
    mock_pw.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.executions.AsyncSessionLocal", factory), \
         patch("app.api.executions.async_playwright", return_value=mock_pw):
        await _run_execution_bg(exe_id, steps_data, base_url, "option_a", 10, queue)

    items = []
    while not queue.empty():
        items.append(queue.get_nowait())

    # Should be 2 step events + 1 sentinel
    step_events = [i for i in items if i is not None]
    assert len(step_events) == 2
    for i, evt in enumerate(step_events):
        assert evt["step_index"] == i
        assert "tier" in evt
        assert "success" in evt
        assert "duration_ms" in evt


@pytest.mark.asyncio
async def test_run_execution_bg_fails_gracefully_on_playwright_error():
    """If Playwright fails to launch, execution status must become 'failed'."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from app.core.database import Base
    from app.models.execution import Execution
    from app.models.test_case import TestCase
    from app.api.executions import _run_execution_bg

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        tc = TestCase(title="T", url="https://example.com",
                      steps=[{"action": "navigate", "instruction": "go", "value": "https://example.com", "selector": None}])
        db.add(tc)
        await db.flush()
        exe = Execution(test_case_id=tc.id, strategy="option_a", status="pending")
        db.add(exe)
        await db.commit()
        exe_id = exe.id
        steps_data = tc.steps
        base_url = tc.url

    queue: asyncio.Queue = asyncio.Queue()

    mock_pw = AsyncMock()
    mock_pw.__aenter__ = AsyncMock(side_effect=RuntimeError("chromium launch failed"))
    mock_pw.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.executions.AsyncSessionLocal", factory), \
         patch("app.api.executions.async_playwright", return_value=mock_pw):
        await _run_execution_bg(exe_id, steps_data, base_url, "option_a", 10, queue)

    async with factory() as db:
        exe = await db.get(Execution, exe_id)
        assert exe.status == "failed"
        assert exe.finished_at is not None

    # Drain queue — sentinel (None) must be present even on failure
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    assert items[-1] is None, "Sentinel (None) must be last item even on failure"
    error_events = [i for i in items if isinstance(i, dict) and i.get("type") == "error"]
    assert len(error_events) == 1
    assert "chromium launch failed" in error_events[0]["message"]
