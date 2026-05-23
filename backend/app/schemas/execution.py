from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict

VALID_STRATEGIES = Literal["option_a", "option_b", "option_c"]


class ExecutionCreate(BaseModel):
    test_case_id: int
    strategy: Optional[VALID_STRATEGIES] = None


class ExecutionStartResponse(BaseModel):
    execution_id: int
    status: str


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


class ExecutionSummary(BaseModel):
    """Execution list item with aggregated per-tier step counts."""

    id: int
    test_case_id: int
    strategy: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    total_steps: int = 0
    tier1_count: int = 0
    tier2_count: int = 0
    tier3_count: int = 0
    success_count: int = 0
