"""Three-tier orchestrator — the portfolio centrepiece.

Executes a single test step through the cascading tier strategy:

  option_a: Tier 1 → Tier 2
  option_b: Tier 1 → Tier 3
  option_c: Tier 1 → Tier 2 → Tier 3

After each step the result is:
- Persisted as an ExecutionStep row in the DB.
- Put onto an optional asyncio.Queue for SSE streaming.
"""

import asyncio
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import ExecutionStep
from app.services.models import Step, TierResult
from app.services.stagehand_adapter import BaseStagehand, get_stagehand
from app.services.tier1_playwright import Tier1PlaywrightExecutor
from app.services.tier2_hybrid import Tier2HybridExecutor
from app.services.tier3_stagehand import Tier3StagehandExecutor
from app.services.xpath_cache_service import XPathCacheService


class ThreeTierService:
    def __init__(
        self,
        db: AsyncSession,
        stagehand: Optional[BaseStagehand] = None,
        timeout_seconds: float = 10,
    ) -> None:
        self.db = db
        _stagehand = stagehand or get_stagehand()
        _cache = XPathCacheService(db)

        self.tier1 = Tier1PlaywrightExecutor(timeout_seconds=timeout_seconds)
        self.tier2 = Tier2HybridExecutor(
            xpath_cache=_cache, stagehand=_stagehand, timeout_seconds=timeout_seconds
        )
        self.tier3 = Tier3StagehandExecutor(stagehand=_stagehand)

    async def execute_step(
        self,
        page,
        step: Step,
        strategy: str,
        execution_id: int,
        step_index: int,
        progress_queue: Optional[asyncio.Queue] = None,
    ) -> TierResult:
        """Execute *step* using the tier cascade defined by *strategy*.

        Args:
            page:           Playwright Page object (or compatible mock).
            step:           The Step to execute.
            strategy:       One of "option_a", "option_b", "option_c".
            execution_id:   FK for the parent Execution row.
            step_index:     Zero-based position of this step in the sequence.
            progress_queue: If provided, the final TierResult is put on this queue
                            for SSE streaming.

        Returns:
            The TierResult produced by whichever tier handled the step.
        """
        result = await self.tier1.execute_step(page, step)

        if not result.success:
            if strategy == "option_a":
                result = await self.tier2.execute_step(page, step)
            elif strategy == "option_b":
                result = await self.tier3.execute_step(page, step)
            elif strategy == "option_c":
                result = await self.tier2.execute_step(page, step)
                if not result.success:
                    result = await self.tier3.execute_step(page, step)

        await self._persist_step(execution_id, step_index, step, result)

        if progress_queue is not None:
            await progress_queue.put(result)

        return result

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    async def _persist_step(
        self,
        execution_id: int,
        step_index: int,
        step: Step,
        result: TierResult,
    ) -> None:
        db_step = ExecutionStep(
            execution_id=execution_id,
            step_index=step_index,
            instruction=step.instruction,
            tier_used=result.tier,
            success=result.success,
            duration_ms=result.duration_ms,
            error=result.error,
            xpath_cached=result.xpath_cached,
        )
        self.db.add(db_step)
        await self.db.commit()
