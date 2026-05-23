"""
Tests for XPathCacheService (RED → GREEN with TDD).

Covers:
- SHA-256 keying of instruction text
- URL normalisation (strip query params / fragments)
- Cache miss returns None
- Cache hit returns xpath and increments hit_count
- Store creates new entry
- Store updates existing entry (upsert)
"""

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STAGEHAND_MOCK", "true")


@pytest_asyncio.fixture
async def db_session():
    from app.core.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# SHA-256 keying
# ─────────────────────────────────────────────────────────────────────────────


def test_hash_instruction_is_deterministic():
    from app.services.xpath_cache_service import _hash_instruction

    h1 = _hash_instruction("click the login button")
    h2 = _hash_instruction("click the login button")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_hash_instruction_differs_for_different_text():
    from app.services.xpath_cache_service import _hash_instruction

    assert _hash_instruction("click login") != _hash_instruction("click logout")


# ─────────────────────────────────────────────────────────────────────────────
# URL normalisation
# ─────────────────────────────────────────────────────────────────────────────


def test_normalise_url_strips_query_params():
    from app.services.xpath_cache_service import _normalise_url

    assert _normalise_url("https://example.com/page?q=1&foo=bar") == "https://example.com/page"


def test_normalise_url_strips_fragment():
    from app.services.xpath_cache_service import _normalise_url

    assert _normalise_url("https://example.com/page#section") == "https://example.com/page"


def test_normalise_url_preserves_path():
    from app.services.xpath_cache_service import _normalise_url

    assert _normalise_url("https://example.com/a/b/c") == "https://example.com/a/b/c"


# ─────────────────────────────────────────────────────────────────────────────
# Cache miss
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_returns_none_on_cache_miss(db_session):
    from app.services.xpath_cache_service import XPathCacheService

    svc = XPathCacheService(db_session)
    result = await svc.get("click the login button", "https://example.com/login")
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Store + get (cache hit)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_then_get_returns_xpath(db_session):
    from app.services.xpath_cache_service import XPathCacheService

    svc = XPathCacheService(db_session)
    await svc.store("click login", "https://example.com/login", "//button[@id='login']")
    result = await svc.get("click login", "https://example.com/login")
    assert result == "//button[@id='login']"


@pytest.mark.asyncio
async def test_get_increments_hit_count(db_session):
    from sqlalchemy import select

    from app.models.xpath_cache import XPathCache
    from app.services.xpath_cache_service import XPathCacheService, _hash_instruction, _normalise_url

    svc = XPathCacheService(db_session)
    instruction = "click submit"
    url = "https://example.com/form"
    await svc.store(instruction, url, "//button[text()='Submit']")

    # hit twice
    await svc.get(instruction, url)
    await svc.get(instruction, url)

    stmt = select(XPathCache).where(
        XPathCache.instruction_hash == _hash_instruction(instruction),
        XPathCache.url_pattern == _normalise_url(url),
    )
    row = (await db_session.execute(stmt)).scalar_one()
    assert row.hit_count == 2


@pytest.mark.asyncio
async def test_get_updates_last_used_at(db_session):
    from sqlalchemy import select

    from app.models.xpath_cache import XPathCache
    from app.services.xpath_cache_service import XPathCacheService, _hash_instruction, _normalise_url

    svc = XPathCacheService(db_session)
    instruction = "click ok"
    url = "https://example.com/"
    await svc.store(instruction, url, "//button")
    await svc.get(instruction, url)

    stmt = select(XPathCache).where(
        XPathCache.instruction_hash == _hash_instruction(instruction),
        XPathCache.url_pattern == _normalise_url(url),
    )
    row = (await db_session.execute(stmt)).scalar_one()
    assert row.last_used_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# Store is idempotent (upsert)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_upserts_existing_entry(db_session):
    from sqlalchemy import select, func

    from app.models.xpath_cache import XPathCache
    from app.services.xpath_cache_service import XPathCacheService

    svc = XPathCacheService(db_session)
    await svc.store("click btn", "https://example.com/", "//button[1]")
    await svc.store("click btn", "https://example.com/", "//button[2]")

    result = await svc.get("click btn", "https://example.com/")
    assert result == "//button[2]"

    # Only one row should exist
    count_stmt = select(func.count()).select_from(XPathCache)
    count = (await db_session.execute(count_stmt)).scalar_one()
    assert count == 1


# ─────────────────────────────────────────────────────────────────────────────
# URL normalisation used consistently for hits
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_hit_ignores_query_string(db_session):
    from app.services.xpath_cache_service import XPathCacheService

    svc = XPathCacheService(db_session)
    # Store using clean URL
    await svc.store("click btn", "https://example.com/page", "//button")
    # Get using URL with query string — should still hit
    result = await svc.get("click btn", "https://example.com/page?utm=abc")
    assert result == "//button"
