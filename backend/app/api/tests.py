from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.test_case import TestCase
from app.schemas.test_case import TestCaseCreate, TestCaseResponse, TestCaseUpdate

router = APIRouter(prefix="/tests", tags=["tests"])


@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_test_case(payload: TestCaseCreate, db: AsyncSession = Depends(get_db)):
    tc = TestCase(
        title=payload.title,
        url=payload.url,
        steps=[s.model_dump() for s in payload.steps],
    )
    db.add(tc)
    await db.commit()
    await db.refresh(tc)
    return tc


@router.get("", response_model=list[TestCaseResponse])
async def list_test_cases(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestCase).order_by(TestCase.id))
    return result.scalars().all()


@router.get("/{tc_id}", response_model=TestCaseResponse)
async def get_test_case(tc_id: int, db: AsyncSession = Depends(get_db)):
    tc = await db.get(TestCase, tc_id)
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    return tc


@router.put("/{tc_id}", response_model=TestCaseResponse)
async def update_test_case(
    tc_id: int, payload: TestCaseUpdate, db: AsyncSession = Depends(get_db)
):
    tc = await db.get(TestCase, tc_id)
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    tc.title = payload.title
    tc.url = payload.url
    tc.steps = [s.model_dump() for s in payload.steps]
    await db.commit()
    await db.refresh(tc)
    return tc


@router.delete("/{tc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_case(tc_id: int, db: AsyncSession = Depends(get_db)):
    tc = await db.get(TestCase, tc_id)
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    await db.delete(tc)
    await db.commit()
