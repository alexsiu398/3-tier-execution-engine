from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, model_validator

VALID_ACTIONS = Literal["navigate", "click", "fill", "press", "assert_text", "assert_url"]


class TestStepSchema(BaseModel):
    action: VALID_ACTIONS
    instruction: str
    selector: Optional[str] = None
    xpath: Optional[str] = None  # client-friendly alias; merged into selector below
    value: Optional[str] = None

    @model_validator(mode="after")
    def _normalise_xpath(self) -> "TestStepSchema":
        """If selector is absent but xpath was provided, use xpath as selector."""
        if self.selector is None and self.xpath is not None:
            self.selector = self.xpath
        return self


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
