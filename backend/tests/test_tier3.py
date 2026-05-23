"""
Tests for Tier3StagehandExecutor (RED → GREEN TDD).

Covers:
- act() returns True → success
- act() returns False → failure
- act() raises exception → failure with error captured
- Returns tier=3 always
- MockStagehand always returns True (fallback in STAGEHAND_MOCK mode)
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STAGEHAND_MOCK", "true")


def _make_page() -> MagicMock:
    page = MagicMock()
    page.url = "https://example.com"
    return page


def _make_stagehand(act_result=True, act_raises=None) -> MagicMock:
    sh = MagicMock()
    if act_raises:
        sh.act = AsyncMock(side_effect=act_raises)
    else:
        sh.act = AsyncMock(return_value=act_result)
    return sh


# ─────────────────────────────────────────────────────────────────────────────
# act() success
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier3_act_success():
    from app.services.models import Step
    from app.services.tier3_stagehand import Tier3StagehandExecutor

    page = _make_page()
    stagehand = _make_stagehand(act_result=True)
    executor = Tier3StagehandExecutor(stagehand=stagehand)
    step = Step(action="click", instruction="click the Buy Now button")

    result = await executor.execute_step(page, step)

    assert result.success is True
    assert result.tier == 3
    assert result.duration_ms >= 0
    stagehand.act.assert_called_once_with("click the Buy Now button")


# ─────────────────────────────────────────────────────────────────────────────
# act() failure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier3_act_returns_false():
    from app.services.models import Step
    from app.services.tier3_stagehand import Tier3StagehandExecutor

    page = _make_page()
    stagehand = _make_stagehand(act_result=False)
    executor = Tier3StagehandExecutor(stagehand=stagehand)
    step = Step(action="click", instruction="click mystery element")

    result = await executor.execute_step(page, step)

    assert result.success is False
    assert result.tier == 3
    assert result.error is None  # no exception, just False return


# ─────────────────────────────────────────────────────────────────────────────
# act() raises an exception
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier3_act_raises_exception():
    from app.services.models import Step
    from app.services.tier3_stagehand import Tier3StagehandExecutor

    page = _make_page()
    stagehand = _make_stagehand(act_raises=RuntimeError("LLM timeout"))
    executor = Tier3StagehandExecutor(stagehand=stagehand)
    step = Step(action="click", instruction="click the button")

    result = await executor.execute_step(page, step)

    assert result.success is False
    assert result.tier == 3
    assert "LLM timeout" in result.error


# ─────────────────────────────────────────────────────────────────────────────
# MockStagehand (STAGEHAND_MOCK=true) always acts successfully
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier3_mock_stagehand_succeeds():
    from app.services.models import Step
    from app.services.stagehand_adapter import MockStagehand
    from app.services.tier3_stagehand import Tier3StagehandExecutor

    executor = Tier3StagehandExecutor(stagehand=MockStagehand())
    step = Step(action="click", instruction="do something complex")

    result = await executor.execute_step(_make_page(), step)

    assert result.success is True
    assert result.tier == 3


# ─────────────────────────────────────────────────────────────────────────────
# duration is always recorded even on failure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier3_duration_recorded_on_failure():
    from app.services.models import Step
    from app.services.tier3_stagehand import Tier3StagehandExecutor

    page = _make_page()
    stagehand = _make_stagehand(act_raises=Exception("oops"))
    executor = Tier3StagehandExecutor(stagehand=stagehand)
    step = Step(action="click", instruction="click btn")

    result = await executor.execute_step(page, step)

    assert result.duration_ms >= 0
