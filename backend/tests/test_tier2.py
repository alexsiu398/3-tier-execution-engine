"""
Tests for Tier2HybridExecutor (RED → GREEN TDD).

Covers:
- Cache hit: locates element via cached XPath, returns tier=2, xpath_cached=True
- Cache miss: calls stagehand.observe(), stores result in cache, returns xpath_cached=False
- observe() returning None → failure
- Playwright locator failure on cached XPath → failure
- store() called exactly once on cache miss
- Element interaction dispatched correctly (click, fill, press, assert_text)
"""

import os
from unittest.mock import AsyncMock, MagicMock, call

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STAGEHAND_MOCK", "true")


def _make_page(url: str = "https://example.com") -> MagicMock:
    page = MagicMock()
    page.url = url
    locator = MagicMock()
    locator.click = AsyncMock()
    locator.fill = AsyncMock()
    locator.press = AsyncMock()
    locator.wait_for = AsyncMock()
    locator.inner_text = AsyncMock(return_value="Hello")
    page.locator = MagicMock(return_value=locator)
    return page


def _make_cache(cached_xpath=None) -> MagicMock:
    cache = MagicMock()
    cache.get = AsyncMock(return_value=cached_xpath)
    cache.store = AsyncMock()
    return cache


def _make_stagehand(observe_result="//button", act_result=True) -> MagicMock:
    sh = MagicMock()
    sh.observe = AsyncMock(return_value=observe_result)
    sh.act = AsyncMock(return_value=act_result)
    return sh


# ─────────────────────────────────────────────────────────────────────────────
# Cache hit
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier2_cache_hit_returns_tier2_cached():
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page()
    cache = _make_cache(cached_xpath="//button[@id='login']")
    stagehand = _make_stagehand()

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="click", instruction="click login button")

    result = await executor.execute_step(page, step)

    assert result.success is True
    assert result.tier == 2
    assert result.xpath_cached is True
    stagehand.observe.assert_not_called()
    cache.store.assert_not_called()


@pytest.mark.asyncio
async def test_tier2_cache_hit_uses_correct_xpath_locator():
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page()
    cache = _make_cache(cached_xpath="//button[@id='login']")
    stagehand = _make_stagehand()

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="click", instruction="click login button")

    await executor.execute_step(page, step)

    page.locator.assert_called_with("xpath=//button[@id='login']")


# ─────────────────────────────────────────────────────────────────────────────
# Cache miss → observe → store → execute
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier2_cache_miss_calls_observe(mock_stagehand=None):
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page()
    cache = _make_cache(cached_xpath=None)
    stagehand = _make_stagehand(observe_result="//a[@href='/login']")

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="click", instruction="click login link")

    result = await executor.execute_step(page, step)

    assert result.success is True
    assert result.tier == 2
    assert result.xpath_cached is False
    stagehand.observe.assert_called_once_with("click login link")


@pytest.mark.asyncio
async def test_tier2_cache_miss_stores_observed_xpath():
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page(url="https://example.com/login")
    cache = _make_cache(cached_xpath=None)
    stagehand = _make_stagehand(observe_result="//input[@name='email']")

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="click", instruction="click email field")

    await executor.execute_step(page, step)

    cache.store.assert_called_once_with(
        "click email field", "https://example.com/login", "//input[@name='email']"
    )


@pytest.mark.asyncio
async def test_tier2_store_called_only_once_on_cache_miss():
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page()
    cache = _make_cache(cached_xpath=None)
    stagehand = _make_stagehand()

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="click", instruction="click btn")

    await executor.execute_step(page, step)

    assert cache.store.call_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# observe returns None → failure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier2_observe_none_returns_failure():
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page()
    cache = _make_cache(cached_xpath=None)
    stagehand = _make_stagehand(observe_result=None)

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="click", instruction="click mystery button")

    result = await executor.execute_step(page, step)

    assert result.success is False
    assert result.tier == 2
    assert result.error is not None


# ─────────────────────────────────────────────────────────────────────────────
# Playwright locator raises on cached XPath → failure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier2_cached_xpath_playwright_error_returns_failure():
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page()
    page.locator.return_value.click = AsyncMock(side_effect=Exception("Element not found"))
    cache = _make_cache(cached_xpath="//button[@stale='true']")
    stagehand = _make_stagehand()

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="click", instruction="click stale button")

    result = await executor.execute_step(page, step)

    assert result.success is False
    assert result.tier == 2


# ─────────────────────────────────────────────────────────────────────────────
# fill action via XPath
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier2_fill_via_cached_xpath():
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page()
    cache = _make_cache(cached_xpath="//input[@name='email']")
    stagehand = _make_stagehand()

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="fill", instruction="fill email", value="user@example.com")

    result = await executor.execute_step(page, step)

    assert result.success is True
    page.locator.return_value.fill.assert_called_once_with("user@example.com")


# ─────────────────────────────────────────────────────────────────────────────
# assert_text action via XPath
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tier2_assert_text_matching_via_cached_xpath():
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page()
    page.locator.return_value.inner_text = AsyncMock(return_value="Welcome back!")
    cache = _make_cache(cached_xpath="//h1")
    stagehand = _make_stagehand()

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="assert_text", instruction="check welcome header", value="Welcome")

    result = await executor.execute_step(page, step)

    assert result.success is True


@pytest.mark.asyncio
async def test_tier2_assert_text_mismatch_via_cached_xpath():
    from app.services.models import Step
    from app.services.tier2_hybrid import Tier2HybridExecutor

    page = _make_page()
    page.locator.return_value.inner_text = AsyncMock(return_value="Error!")
    cache = _make_cache(cached_xpath="//h1")
    stagehand = _make_stagehand()

    executor = Tier2HybridExecutor(xpath_cache=cache, stagehand=stagehand)
    step = Step(action="assert_text", instruction="check welcome", value="Welcome")

    result = await executor.execute_step(page, step)

    assert result.success is False
