"""
Tests for Tier1PlaywrightExecutor (RED → GREEN TDD).

Covers:
- navigate action success
- click with selector success
- click without selector → failure
- fill action success / missing selector
- press action success
- assert_text: matching text → success
- assert_text: wrong text → failure
- assert_url: matching → success / mismatch → failure
- timeout → failure with error message
- unsupported action → failure
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STAGEHAND_MOCK", "true")


def _make_page(url: str = "https://example.com") -> MagicMock:
    """Build a minimal mock Playwright page."""
    page = MagicMock()
    page.url = url
    page.goto = AsyncMock()
    locator = MagicMock()
    locator.click = AsyncMock()
    locator.fill = AsyncMock()
    locator.press = AsyncMock()
    locator.wait_for = AsyncMock()
    locator.inner_text = AsyncMock(return_value="Hello World")
    page.locator = MagicMock(return_value=locator)
    return page


# ─────────────────────────────────────────────────────────────────────────────
# navigate
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier1_navigate_success():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="navigate", instruction="go to example", value="https://example.com")

    result = await executor.execute_step(page, step)

    assert result.success is True
    assert result.tier == 1
    assert result.duration_ms >= 0
    page.goto.assert_called_once_with("https://example.com", timeout=10000)


@pytest.mark.asyncio
async def test_tier1_navigate_uses_instruction_when_no_value():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="navigate", instruction="https://playwright.dev")

    result = await executor.execute_step(page, step)

    assert result.success is True
    page.goto.assert_called_once_with("https://playwright.dev", timeout=10000)


# ─────────────────────────────────────────────────────────────────────────────
# click
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier1_click_with_selector_success():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="click", instruction="click login", selector="#login-btn")

    result = await executor.execute_step(page, step)

    assert result.success is True
    assert result.tier == 1
    page.locator.assert_called_once_with("#login-btn")
    page.locator.return_value.click.assert_called_once()


@pytest.mark.asyncio
async def test_tier1_click_without_selector_fails():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="click", instruction="click the submit button")

    result = await executor.execute_step(page, step)

    assert result.success is False
    assert result.tier == 1
    assert "selector" in result.error.lower()


# ─────────────────────────────────────────────────────────────────────────────
# fill
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier1_fill_success():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="fill", instruction="enter email", selector="#email", value="test@example.com")

    result = await executor.execute_step(page, step)

    assert result.success is True
    page.locator.return_value.fill.assert_called_once_with("test@example.com", timeout=10000)


@pytest.mark.asyncio
async def test_tier1_fill_without_selector_fails():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="fill", instruction="fill in the email field", value="x@y.com")

    result = await executor.execute_step(page, step)

    assert result.success is False
    assert "selector" in result.error.lower()


# ─────────────────────────────────────────────────────────────────────────────
# press
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier1_press_success():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="press", instruction="press enter", selector="#search", value="Enter")

    result = await executor.execute_step(page, step)

    assert result.success is True
    page.locator.return_value.press.assert_called_once_with("Enter", timeout=10000)


@pytest.mark.asyncio
async def test_tier1_press_defaults_to_enter():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="press", instruction="press enter", selector="input")

    result = await executor.execute_step(page, step)

    assert result.success is True
    page.locator.return_value.press.assert_called_once_with("Enter", timeout=10000)


# ─────────────────────────────────────────────────────────────────────────────
# assert_text
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier1_assert_text_matching():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    page.locator.return_value.inner_text = AsyncMock(return_value="Welcome back!")
    executor = Tier1PlaywrightExecutor()
    step = Step(action="assert_text", instruction="check welcome text", selector="h1", value="Welcome")

    result = await executor.execute_step(page, step)

    assert result.success is True


@pytest.mark.asyncio
async def test_tier1_assert_text_mismatch():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    page.locator.return_value.inner_text = AsyncMock(return_value="Error 404")
    executor = Tier1PlaywrightExecutor()
    step = Step(action="assert_text", instruction="check welcome text", selector="h1", value="Welcome")

    result = await executor.execute_step(page, step)

    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_tier1_assert_text_without_selector_fails():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="assert_text", instruction="check page says hello", value="hello")

    result = await executor.execute_step(page, step)

    assert result.success is False


# ─────────────────────────────────────────────────────────────────────────────
# assert_url
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier1_assert_url_matching():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page(url="https://example.com/dashboard")
    executor = Tier1PlaywrightExecutor()
    step = Step(action="assert_url", instruction="verify dashboard", value="/dashboard")

    result = await executor.execute_step(page, step)

    assert result.success is True


@pytest.mark.asyncio
async def test_tier1_assert_url_mismatch():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page(url="https://example.com/login")
    executor = Tier1PlaywrightExecutor()
    step = Step(action="assert_url", instruction="verify dashboard", value="/dashboard")

    result = await executor.execute_step(page, step)

    assert result.success is False


# ─────────────────────────────────────────────────────────────────────────────
# timeout
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier1_timeout_returns_failure():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    # Simulate Playwright raising its native TimeoutError (not asyncio.wait_for).
    # After the fix, Playwright's own timeout fires through the normal exception path.
    page.goto = AsyncMock(side_effect=asyncio.TimeoutError("Timeout 10ms exceeded."))
    executor = Tier1PlaywrightExecutor(timeout_seconds=0.01)
    step = Step(action="navigate", instruction="go somewhere", value="https://slow.example.com")

    result = await executor.execute_step(page, step)

    assert result.success is False
    assert result.tier == 1
    assert result.error is not None


@pytest.mark.asyncio
async def test_tier1_no_asyncio_wait_for_used():
    """Tier1 must NOT wrap Playwright calls in asyncio.wait_for.

    asyncio.wait_for creates an internal Task; when cancelled it leaves Playwright's
    internal Futures unresolved, producing TargetClosedError 'Future exception was
    never retrieved' when the browser closes.
    Playwright's own per-call timeout= parameter is the correct mechanism.
    """
    import inspect
    from app.services import tier1_playwright

    source = inspect.getsource(tier1_playwright)
    assert "asyncio.wait_for" not in source, (
        "tier1_playwright must not use asyncio.wait_for — use Playwright native timeout= instead"
    )


# ─────────────────────────────────────────────────────────────────────────────
# unsupported action
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier1_unsupported_action_returns_failure():
    from app.services.models import Step
    from app.services.tier1_playwright import Tier1PlaywrightExecutor

    page = _make_page()
    executor = Tier1PlaywrightExecutor()
    step = Step(action="hover", instruction="hover over menu")

    result = await executor.execute_step(page, step)

    assert result.success is False
    assert "unsupported" in result.error.lower()
