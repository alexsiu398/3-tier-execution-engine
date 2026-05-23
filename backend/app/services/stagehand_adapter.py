"""Stagehand adapter — decouples the Stagehand dependency from the execution tiers.

MockStagehand is the default (STAGEHAND_MOCK=true / STAGEHAND_ENABLED=false).
The real adapter is opt-in and not yet implemented (requires Node.js Stagehand via CDP).
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseStagehand(ABC):
    """Abstract interface for any Stagehand adapter."""

    @abstractmethod
    async def observe(self, instruction: str) -> Optional[str]:
        """Return an XPath for the element described by *instruction*, or None."""
        ...

    @abstractmethod
    async def act(self, instruction: str) -> bool:
        """Execute *instruction* via AI reasoning. Return True on success."""
        ...


class MockStagehand(BaseStagehand):
    """Canned mock adapter for CI / offline demo (STAGEHAND_MOCK=true).

    observe() returns a predictable generic XPath so that the cache layer can
    be exercised in tests; act() always succeeds.
    """

    async def observe(self, instruction: str) -> Optional[str]:
        # Return a plausible generic XPath that exercises cache logic
        return "//button[1]"

    async def act(self, instruction: str) -> bool:
        return True


def get_stagehand() -> BaseStagehand:
    """Factory: return the appropriate Stagehand adapter based on env config."""
    from app.core.config import settings

    if settings.STAGEHAND_MOCK or not settings.STAGEHAND_ENABLED:
        return MockStagehand()

    # Real CDP-based adapter would be instantiated here.
    raise NotImplementedError(
        "Real Stagehand adapter is not yet implemented. "
        "Set STAGEHAND_MOCK=true or STAGEHAND_ENABLED=false."
    )
