from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.execution_settings import ExecutionSettings
from app.schemas.settings import ExecutionSettingsResponse, ExecutionSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


async def _get_or_create_settings(db: AsyncSession) -> ExecutionSettings:
    result = await db.execute(select(ExecutionSettings).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        row = ExecutionSettings()
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


@router.get("", response_model=ExecutionSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await _get_or_create_settings(db)


@router.put("", response_model=ExecutionSettingsResponse)
async def update_settings(payload: ExecutionSettingsUpdate, db: AsyncSession = Depends(get_db)):
    row = await _get_or_create_settings(db)
    row.fallback_strategy = payload.fallback_strategy
    row.timeout_per_tier_seconds = payload.timeout_per_tier_seconds
    row.max_retry_per_tier = payload.max_retry_per_tier
    await db.commit()
    await db.refresh(row)
    return row
