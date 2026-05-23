"""Tier 2 — Hybrid XPath executor.

Cache-first strategy:
1. Look up instruction hash in XPath cache.
2. Hit  → execute directly via Playwright using cached XPath.
3. Miss → call stagehand.observe() to get live XPath,
          persist XPath to cache,
          execute via Playwright.

Returns TierResult(tier=2, xpath_cached=True/False).
"""

import time
from typing import Optional

from app.services.models import Step, TierResult
from app.services.stagehand_adapter import BaseStagehand
from app.services.xpath_cache_service import XPathCacheService


class Tier2HybridExecutor:
    def __init__(
        self,
        xpath_cache: XPathCacheService,
        stagehand: BaseStagehand,
        timeout_seconds: float = 10,
    ) -> None:
        self.xpath_cache = xpath_cache
        self.stagehand = stagehand
        self.timeout_seconds = timeout_seconds
        # Playwright accepts timeout in milliseconds
        self.timeout_ms = int(timeout_seconds * 1000)

    async def execute_step(self, page, step: Step) -> TierResult:
        start = time.monotonic()
        page_url: str = page.url

        try:
            cached_xpath = await self.xpath_cache.get(step.instruction, page_url)

            if cached_xpath:
                await self._execute_with_xpath(page, step, cached_xpath)
                return TierResult(
                    tier=2,
                    success=True,
                    duration_ms=(time.monotonic() - start) * 1000,
                    xpath_cached=True,
                )

            # Cache miss — ask Stagehand to observe the DOM
            xpath = await self.stagehand.observe(step.instruction)
            if not xpath:
                raise ValueError("stagehand.observe() returned no XPath for this instruction")

            await self._execute_with_xpath(page, step, xpath)
            await self.xpath_cache.store(step.instruction, page_url, xpath)

            return TierResult(
                tier=2,
                success=True,
                duration_ms=(time.monotonic() - start) * 1000,
                xpath_cached=False,
            )

        except Exception as exc:
            return TierResult(
                tier=2,
                success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(exc),
            )

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    async def _execute_with_xpath(self, page, step: Step, xpath: str) -> None:
        """Dispatch the step's action using the resolved *xpath*."""
        t = self.timeout_ms
        locator = page.locator(f"xpath={xpath}")
        action = step.action

        if action == "click":
            await locator.click(timeout=t)
        elif action == "fill":
            await locator.fill(step.value or "", timeout=t)
        elif action == "press":
            await locator.press(step.value or "Enter", timeout=t)
        elif action == "assert_text":
            text = await locator.inner_text(timeout=t)
            if step.value and step.value not in text:
                raise AssertionError(f"Expected '{step.value}' not found in '{text}'")
        else:
            raise ValueError(f"Tier 2 cannot handle action: '{action}'")
