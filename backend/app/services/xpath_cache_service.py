"""XPath cache service — SHA-256 keyed lookup and upsert."""

import hashlib
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.xpath_cache import XPathCache


def _hash_instruction(instruction: str) -> str:
    """Return a SHA-256 hex digest of the instruction text."""
    return hashlib.sha256(instruction.encode()).hexdigest()


def _normalise_url(url: str) -> str:
    """Strip query string and fragment from a URL for cache key matching."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


class XPathCacheService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, instruction: str, page_url: str) -> Optional[str]:
        """Return cached XPath string, or None on miss.

        Increments hit_count and updates last_used_at on a hit.
        """
        hash_ = _hash_instruction(instruction)
        normalised = _normalise_url(page_url)

        stmt = select(XPathCache).where(
            XPathCache.instruction_hash == hash_,
            XPathCache.url_pattern == normalised,
        )
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        row.hit_count += 1
        row.last_used_at = datetime.now(timezone.utc)
        await self.db.commit()
        return row.xpath

    async def store(self, instruction: str, page_url: str, xpath: str) -> None:
        """Upsert an XPath cache entry."""
        hash_ = _hash_instruction(instruction)
        normalised = _normalise_url(page_url)

        stmt = select(XPathCache).where(
            XPathCache.instruction_hash == hash_,
            XPathCache.url_pattern == normalised,
        )
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            row = XPathCache(
                instruction_hash=hash_,
                url_pattern=normalised,
                xpath=xpath,
            )
            self.db.add(row)
        else:
            row.xpath = xpath

        await self.db.commit()
