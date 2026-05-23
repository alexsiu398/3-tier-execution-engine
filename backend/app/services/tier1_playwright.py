"""Tier 1 — Playwright direct executor.

Executes test steps using explicit CSS/XPath selectors with no LLM involvement.
Expected to handle ~85 % of steps at zero AI cost.

Supported actions: navigate, click, fill, press, assert_text, assert_url.
"""

import time

from app.services.models import Step, TierResult


class Tier1PlaywrightExecutor:
    def __init__(self, timeout_seconds: float = 10) -> None:
        self.timeout_seconds = timeout_seconds
        # Playwright accepts timeout in milliseconds
        self.timeout_ms = int(timeout_seconds * 1000)

    async def execute_step(self, page, step: Step) -> TierResult:
        """Run *step* on *page*. Always returns a TierResult(tier=1, …)."""
        start = time.monotonic()
        try:
            await self._run(page, step)
            return TierResult(tier=1, success=True, duration_ms=(time.monotonic() - start) * 1000)
        except Exception as exc:
            return TierResult(
                tier=1,
                success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(exc),
            )

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    async def _run(self, page, step: Step) -> None:
        action = step.action
        t = self.timeout_ms

        if action == "navigate":
            await page.goto(step.value or step.instruction, timeout=t)

        elif action == "click":
            if not step.selector:
                raise ValueError("Tier 1 click requires a selector")
            await page.locator(step.selector).click(timeout=t)

        elif action == "fill":
            if not step.selector:
                raise ValueError("Tier 1 fill requires a selector")
            await page.locator(step.selector).fill(step.value or "", timeout=t)

        elif action == "press":
            if not step.selector:
                raise ValueError("Tier 1 press requires a selector")
            await page.locator(step.selector).press(step.value or "Enter", timeout=t)

        elif action == "assert_text":
            if not step.selector:
                raise ValueError("Tier 1 assert_text requires a selector")
            await page.locator(step.selector).wait_for(timeout=t)
            text = await page.locator(step.selector).inner_text(timeout=t)
            if step.value and step.value not in text:
                raise AssertionError(f"Expected text '{step.value}' not found in '{text}'")

        elif action == "assert_url":
            expected = step.value or step.instruction
            current = page.url
            if expected not in current:
                raise AssertionError(f"Expected URL to contain '{expected}', got '{current}'")

        else:
            raise ValueError(f"Unsupported action: '{action}'")
