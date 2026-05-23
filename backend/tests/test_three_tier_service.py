"""
Tests for ThreeTierService (RED → GREEN TDD).

Covers:
- option_a: Tier1 success → returns Tier1 result (no fallback)
- option_a: Tier1 fail → Tier2 attempted
- option_b: Tier1 fail → Tier3 attempted (Tier2 skipped)
- option_c: Tier1 fail → Tier2 fail → Tier3
- option_c: Tier1 fail → Tier2 success → Tier3 NOT called
- Tier1 success → Tier2 and Tier3 NOT called (all strategies)
- Progress queue receives result
- ExecutionStep is persisted to DB
- Mid-run failure propagation returns correct tier
"""

import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STAGEHAND_MOCK", "true")


@pytest_asyncio.fixture
async def db_session():
    from app.core.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _tier_result(tier: int, success: bool, duration_ms: float = 10.0, xpath_cached: bool = False):
    from app.services.models import TierResult

    return TierResult(tier=tier, success=success, duration_ms=duration_ms, xpath_cached=xpath_cached)


def _step(action="click", instruction="click btn", selector="#btn"):
    from app.services.models import Step

    return Step(action=action, instruction=instruction, selector=selector)


def _make_page() -> MagicMock:
    page = MagicMock()
    page.url = "https://example.com"
    return page


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build service with mocked sub-executors
# ─────────────────────────────────────────────────────────────────────────────


def _make_service(db, tier1_result, tier2_result=None, tier3_result=None):
    from app.services.three_tier_service import ThreeTierService

    svc = ThreeTierService.__new__(ThreeTierService)
    svc.db = db

    svc.tier1 = MagicMock()
    svc.tier1.execute_step = AsyncMock(return_value=tier1_result)

    svc.tier2 = MagicMock()
    svc.tier2.execute_step = AsyncMock(return_value=tier2_result or _tier_result(2, False))

    svc.tier3 = MagicMock()
    svc.tier3.execute_step = AsyncMock(return_value=tier3_result or _tier_result(3, True))

    return svc


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1 success: always returns without escalating
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier1_success_no_escalation_option_a(db_session):
    svc = _make_service(db_session, tier1_result=_tier_result(1, True))
    page = _make_page()

    result = await svc.execute_step(page, _step(), "option_a", execution_id=1, step_index=0)

    assert result.tier == 1
    assert result.success is True
    svc.tier2.execute_step.assert_not_called()
    svc.tier3.execute_step.assert_not_called()


@pytest.mark.asyncio
async def test_tier1_success_no_escalation_option_b(db_session):
    svc = _make_service(db_session, tier1_result=_tier_result(1, True))
    result = await svc.execute_step(_make_page(), _step(), "option_b", execution_id=1, step_index=0)

    assert result.tier == 1
    svc.tier3.execute_step.assert_not_called()


@pytest.mark.asyncio
async def test_tier1_success_no_escalation_option_c(db_session):
    svc = _make_service(db_session, tier1_result=_tier_result(1, True))
    result = await svc.execute_step(_make_page(), _step(), "option_c", execution_id=1, step_index=0)

    assert result.tier == 1
    svc.tier2.execute_step.assert_not_called()
    svc.tier3.execute_step.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# option_a: Tier1 fail → Tier2
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_option_a_tier1_fail_escalates_to_tier2(db_session):
    svc = _make_service(
        db_session,
        tier1_result=_tier_result(1, False),
        tier2_result=_tier_result(2, True),
    )

    result = await svc.execute_step(_make_page(), _step(), "option_a", execution_id=1, step_index=0)

    assert result.tier == 2
    assert result.success is True
    svc.tier2.execute_step.assert_called_once()
    svc.tier3.execute_step.assert_not_called()


@pytest.mark.asyncio
async def test_option_a_tier1_fail_tier2_fail_no_tier3(db_session):
    svc = _make_service(
        db_session,
        tier1_result=_tier_result(1, False),
        tier2_result=_tier_result(2, False),
    )

    result = await svc.execute_step(_make_page(), _step(), "option_a", execution_id=1, step_index=0)

    assert result.tier == 2
    assert result.success is False
    svc.tier3.execute_step.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# option_b: Tier1 fail → Tier3 (skip Tier2)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_option_b_tier1_fail_escalates_to_tier3(db_session):
    svc = _make_service(
        db_session,
        tier1_result=_tier_result(1, False),
        tier3_result=_tier_result(3, True),
    )

    result = await svc.execute_step(_make_page(), _step(), "option_b", execution_id=1, step_index=0)

    assert result.tier == 3
    assert result.success is True
    svc.tier2.execute_step.assert_not_called()
    svc.tier3.execute_step.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# option_c: full cascade Tier1 → Tier2 → Tier3
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_option_c_tier1_fail_tier2_fail_escalates_to_tier3(db_session):
    svc = _make_service(
        db_session,
        tier1_result=_tier_result(1, False),
        tier2_result=_tier_result(2, False),
        tier3_result=_tier_result(3, True),
    )

    result = await svc.execute_step(_make_page(), _step(), "option_c", execution_id=1, step_index=0)

    assert result.tier == 3
    assert result.success is True
    svc.tier2.execute_step.assert_called_once()
    svc.tier3.execute_step.assert_called_once()


@pytest.mark.asyncio
async def test_option_c_tier1_fail_tier2_success_no_tier3(db_session):
    svc = _make_service(
        db_session,
        tier1_result=_tier_result(1, False),
        tier2_result=_tier_result(2, True),
        tier3_result=_tier_result(3, True),
    )

    result = await svc.execute_step(_make_page(), _step(), "option_c", execution_id=1, step_index=0)

    assert result.tier == 2
    assert result.success is True
    svc.tier3.execute_step.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Progress queue
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_progress_queue_receives_result(db_session):
    svc = _make_service(db_session, tier1_result=_tier_result(1, True))
    queue: asyncio.Queue = asyncio.Queue()

    await svc.execute_step(
        _make_page(), _step(), "option_a", execution_id=1, step_index=0, progress_queue=queue
    )

    assert not queue.empty()
    event = queue.get_nowait()
    assert event.tier == 1


# ─────────────────────────────────────────────────────────────────────────────
# ExecutionStep persistence
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execution_step_persisted_to_db(db_session):
    from sqlalchemy import select

    from app.models.execution import Execution, ExecutionStep
    from app.models.test_case import TestCase

    # Need a TestCase and Execution row for FK constraints
    tc = TestCase(title="T", url="https://example.com", steps=[])
    db_session.add(tc)
    await db_session.flush()

    exe = Execution(test_case_id=tc.id, strategy="option_a", status="running")
    db_session.add(exe)
    await db_session.commit()

    svc = _make_service(db_session, tier1_result=_tier_result(1, True))

    await svc.execute_step(_make_page(), _step(), "option_a", execution_id=exe.id, step_index=0)

    stmt = select(ExecutionStep).where(ExecutionStep.execution_id == exe.id)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].step_index == 0
    assert rows[0].tier_used == 1
    assert rows[0].success is True


@pytest.mark.asyncio
async def test_execution_step_persisted_with_correct_instruction(db_session):
    from sqlalchemy import select

    from app.models.execution import Execution, ExecutionStep
    from app.models.test_case import TestCase

    tc = TestCase(title="T", url="https://example.com", steps=[])
    db_session.add(tc)
    await db_session.flush()

    exe = Execution(test_case_id=tc.id, strategy="option_c", status="running")
    db_session.add(exe)
    await db_session.commit()

    svc = _make_service(db_session, tier1_result=_tier_result(1, False), tier2_result=_tier_result(2, True))
    step = _step(instruction="navigate to home page")

    await svc.execute_step(_make_page(), step, "option_a", execution_id=exe.id, step_index=2)

    stmt = select(ExecutionStep).where(ExecutionStep.execution_id == exe.id)
    row = (await db_session.execute(stmt)).scalar_one()
    assert row.instruction == "navigate to home page"
    assert row.step_index == 2
