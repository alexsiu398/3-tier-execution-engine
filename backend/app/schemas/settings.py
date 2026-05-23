from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict

VALID_STRATEGIES = Literal["option_a", "option_b", "option_c"]


class ExecutionSettingsUpdate(BaseModel):
    fallback_strategy: VALID_STRATEGIES = "option_c"
    timeout_per_tier_seconds: int = 10
    max_retry_per_tier: int = 2


class ExecutionSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fallback_strategy: str
    timeout_per_tier_seconds: int
    max_retry_per_tier: int
