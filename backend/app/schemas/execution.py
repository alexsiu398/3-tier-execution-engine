from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ExecutionStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_index: int
    instruction: str
    tier_used: Optional[int]
    success: Optional[bool]
    duration_ms: Optional[float]
    error: Optional[str]
    xpath_cached: bool


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_case_id: int
    strategy: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    steps: list[ExecutionStepResponse] = []
