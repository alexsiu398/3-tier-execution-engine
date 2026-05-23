from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict

VALID_ACTIONS = Literal["navigate", "click", "fill", "press", "assert_text", "assert_url"]


class TestStepSchema(BaseModel):
    action: VALID_ACTIONS
    instruction: str
    selector: Optional[str] = None
    value: Optional[str] = None


class TestCaseCreate(BaseModel):
    title: str
    url: str
    steps: list[TestStepSchema] = []


class TestCaseUpdate(BaseModel):
    title: str
    url: str
    steps: list[TestStepSchema] = []


class TestCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    steps: list[TestStepSchema]
    created_at: datetime
