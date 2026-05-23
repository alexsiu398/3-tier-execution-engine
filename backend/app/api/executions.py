"""Execution API — Phase 3.

Endpoints:
  POST /api/v1/executions              — create & start execution (202)
  GET  /api/v1/executions              — history list with aggregated tier stats
  GET  /api/v1/executions/{id}         — detail with all steps
  GET  /api/v1/executions/{id}/stream  — SSE real-time progress stream
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from playwright.async_api import async_playwright
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.models.execution import Execution, ExecutionStep
from app.models.execution_settings import ExecutionSettings
from app.models.test_case import TestCase
from app.schemas.execution import (
    ExecutionCreate,
    ExecutionResponse,
    ExecutionStartResponse,
    ExecutionSummary,
)
from app.services.models import Step
from app.services.three_tier_service import ThreeTierService

router = APIRouter(prefix="/executions", tags=["executions"])

# In-memory store for live execution queues (keyed by execution_id)
_execution_queues: dict[int, asyncio.Queue] = {}


# ─────────────────────────────────────────────────────────────────────────────
# POST /executions — start a new execution
# ─────────────────────────────────────────────────────────────────────────────


@router.post("", response_model=ExecutionStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_execution(
    payload: ExecutionCreate,
    db: AsyncSession = Depends(get_db),
) -> ExecutionStartResponse:
    # Validate test case exists
    tc = await db.get(TestCase, payload.test_case_id)
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    # Resolve strategy: explicit > settings row > hard default
    result = await db.execute(select(ExecutionSettings).limit(1))
    settings_row = result.scalar_one_or_none()
    strategy: str = (
        payload.strategy
        or (settings_row.fallback_strategy if settings_row else "option_c")
    )
    timeout: int = settings_row.timeout_per_tier_seconds if settings_row else 10

    # Persist execution row immediately so the caller gets an ID
    execution = Execution(
        test_case_id=payload.test_case_id,
        strategy=strategy,
        status="pending",
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Create progress queue and launch background task
    queue: asyncio.Queue = asyncio.Queue()
    _execution_queues[execution.id] = queue

    asyncio.create_task(
        _run_execution_bg(
            execution_id=execution.id,
            steps_data=list(tc.steps),
            base_url=tc.url,
            strategy=strategy,
            timeout_seconds=timeout,
            queue=queue,
        )
    )

    return ExecutionStartResponse(execution_id=execution.id, status="pending")


# ─────────────────────────────────────────────────────────────────────────────
# Background execution task
# ─────────────────────────────────────────────────────────────────────────────


async def _run_execution_bg(
    execution_id: int,
    steps_data: list,
    base_url: str,
    strategy: str,
    timeout_seconds: int,
    queue: asyncio.Queue,
) -> None:
    """Run every step through ThreeTierService, emit progress events, persist results."""
    async with AsyncSessionLocal() as db:
        execution = await db.get(Execution, execution_id)
        execution.status = "running"
        execution.started_at = datetime.now(timezone.utc)
        await db.commit()

        svc = ThreeTierService(db, timeout_seconds=timeout_seconds)
        steps = [Step(**s) for s in steps_data]

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=False)
                page = await browser.new_page()
                try:
                    for idx, step in enumerate(steps):
                        result = await svc.execute_step(
                            page, step, strategy, execution_id, idx
                        )
                        await queue.put(
                            {
                                "step_index": idx,
                                "tier": result.tier,
                                "success": result.success,
                                "duration_ms": result.duration_ms,
                                "xpath_cached": result.xpath_cached,
                            }
                        )
                finally:
                    await browser.close()

            execution.status = "completed"

        except Exception as exc:
            execution.status = "failed"
            await queue.put({"type": "error", "message": str(exc)})

        finally:
            execution.finished_at = datetime.now(timezone.utc)
            await db.commit()
            # Sentinel signals the SSE generator to close the stream
            await queue.put(None)


# ─────────────────────────────────────────────────────────────────────────────
# GET /executions — history list
# ─────────────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ExecutionSummary])
async def list_executions(db: AsyncSession = Depends(get_db)) -> list[ExecutionSummary]:
    result = await db.execute(select(Execution).order_by(Execution.id.desc()))
    executions = result.scalars().all()

    summaries: list[ExecutionSummary] = []
    for exe in executions:
        steps_result = await db.execute(
            select(ExecutionStep).where(ExecutionStep.execution_id == exe.id)
        )
        steps = steps_result.scalars().all()

        summaries.append(
            ExecutionSummary(
                id=exe.id,
                test_case_id=exe.test_case_id,
                strategy=exe.strategy,
                status=exe.status,
                started_at=exe.started_at,
                finished_at=exe.finished_at,
                total_steps=len(steps),
                tier1_count=sum(1 for s in steps if s.tier_used == 1),
                tier2_count=sum(1 for s in steps if s.tier_used == 2),
                tier3_count=sum(1 for s in steps if s.tier_used == 3),
                success_count=sum(1 for s in steps if s.success),
            )
        )
    return summaries


# ─────────────────────────────────────────────────────────────────────────────
# GET /executions/{id} — detail with steps
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    stmt = (
        select(Execution)
        .where(Execution.id == execution_id)
        .options(selectinload(Execution.steps))
    )
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


# ─────────────────────────────────────────────────────────────────────────────
# GET /executions/{id}/stream — SSE real-time progress
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/{execution_id}/stream")
async def stream_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    # Validate execution exists
    stmt = (
        select(Execution)
        .where(Execution.id == execution_id)
        .options(selectinload(Execution.steps))
    )
    result = await db.execute(stmt)
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    queue: Optional[asyncio.Queue] = _execution_queues.get(execution_id)

    async def _event_generator():
        if queue is None:
            # Execution already finished — replay steps from DB
            for step in sorted(execution.steps, key=lambda s: s.step_index):
                data = json.dumps(
                    {
                        "step_index": step.step_index,
                        "tier": step.tier_used,
                        "success": step.success,
                        "duration_ms": step.duration_ms,
                        "xpath_cached": step.xpath_cached,
                    }
                )
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'status': execution.status})}\n\n"
            return

        # Live execution — drain the queue until sentinel
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    continue

                if event is None:
                    # Sentinel — execution complete
                    _execution_queues.pop(execution_id, None)
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break

                yield f"data: {json.dumps(event)}\n\n"

        except asyncio.CancelledError:
            # Client disconnected
            _execution_queues.pop(execution_id, None)
            raise

    return StreamingResponse(_event_generator(), media_type="text/event-stream")
