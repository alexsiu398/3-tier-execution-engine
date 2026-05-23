"""Tier 3 — Stagehand AI executor (last-resort fallback).

Delegates the full step to Stagehand's act() method which performs LLM-based
DOM reasoning. Expect 10-30 s latency; only called when Tier 1 and Tier 2 fail.
"""

import time

from app.services.models import Step, TierResult
from app.services.stagehand_adapter import BaseStagehand


class Tier3StagehandExecutor:
    def __init__(self, stagehand: BaseStagehand) -> None:
        self.stagehand = stagehand

    async def execute_step(self, page, step: Step) -> TierResult:
        """Call stagehand.act() and return a TierResult(tier=3, …)."""
        start = time.monotonic()
        try:
            success = await self.stagehand.act(step.instruction)
            return TierResult(
                tier=3,
                success=bool(success),
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            return TierResult(
                tier=3,
                success=False,
                duration_ms=(time.monotonic() - start) * 1000,
                error=str(exc),
            )
