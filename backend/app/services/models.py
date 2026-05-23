"""Shared value types for the 3-tier execution engine."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Step:
    """A single test step parsed from a TestCase's JSON steps array."""

    action: str  # navigate | click | fill | press | assert_text | assert_url
    instruction: str  # natural-language description (used by Tier 2/3)
    selector: Optional[str] = None  # optional CSS/XPath selector for Tier 1
    value: Optional[str] = None  # fill value, key name, expected text, …


@dataclass
class TierResult:
    """Result returned by any tier executor."""

    tier: int
    success: bool
    duration_ms: float
    error: Optional[str] = None
    xpath_cached: bool = False
