#!/usr/bin/env python3
"""Seed the database with demo test cases and default settings.

Run via:
    python seed_demo.py          # from inside backend/
    make demo                    # runs migrate then this script

The script is idempotent — it skips insertion if test cases already exist.
"""

import asyncio
import sys
import os

# Make the app package importable when the script is run from backend/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.test_case import TestCase
from app.models.execution_settings import ExecutionSettings

# ---------------------------------------------------------------------------
# Demo test cases — three scenarios that collectively exercise all three tiers:
#
#  Tier 1  — steps with an explicit `selector` field (direct Playwright)
#  Tier 2  — steps without a selector; Stagehand observe() extracts XPath and
#             caches it; subsequent runs hit the cache at near-Tier-1 speed
#  Tier 3  — steps that fail Tiers 1 & 2 and escalate to full LLM act()
#
# In the default STAGEHAND_MOCK=true mode Tier 2/3 return mock results so
# the full cascade is visible without needing an API key.
# ---------------------------------------------------------------------------
DEMO_TEST_CASES = [
    {
        "title": "Example.com — Smoke Test",
        "url": "https://example.com",
        "steps": [
            {
                "action": "navigate",
                "instruction": "Navigate to example.com",
                "value": "https://example.com",
            },
            {
                # selector present → Tier 1 handles this instantly
                "action": "assert_text",
                "instruction": "Verify the page heading reads 'Example Domain'",
                "selector": "h1",
                "value": "Example Domain",
            },
            {
                # selector present → Tier 1
                "action": "assert_text",
                "instruction": "Check that the body contains introductory paragraph text",
                "selector": "p",
                "value": "This domain is for use",
            },
            {
                # selector present → Tier 1
                "action": "click",
                "instruction": "Click the 'More information...' link",
                "selector": "a",
            },
        ],
    },
    {
        "title": "Playwright.dev — Docs Navigation",
        "url": "https://playwright.dev",
        "steps": [
            {
                "action": "navigate",
                "instruction": "Go to the Playwright documentation homepage",
                "value": "https://playwright.dev",
            },
            {
                # selector present → Tier 1
                "action": "assert_text",
                "instruction": "Verify the main heading contains 'Playwright'",
                "selector": "h1",
                "value": "Playwright",
            },
            {
                # No selector — Tier 1 fails, Tier 2 observe() extracts XPath and
                # caches it.  Second run of this test hits the cache: T2-cached.
                "action": "click",
                "instruction": "Click the 'Get started' button on the homepage",
            },
            {
                # No selector — exercises Tier 2 / Tier 3 fallback
                "action": "assert_text",
                "instruction": "Confirm the installation page is showing",
                "value": "Installation",
            },
        ],
    },
    {
        "title": "Wikipedia — Main Page Browsing",
        "url": "https://en.wikipedia.org/wiki/Main_Page",
        "steps": [
            {
                "action": "navigate",
                "instruction": "Open the Wikipedia main page",
                "value": "https://en.wikipedia.org/wiki/Main_Page",
            },
            {
                # selector present → Tier 1
                "action": "assert_text",
                "instruction": "Check that the Wikipedia wordmark is visible",
                "selector": "#p-logo a",
                "value": "Wikipedia",
            },
            {
                # selector present → Tier 1
                "action": "assert_text",
                "instruction": "Verify 'Welcome to Wikipedia' text is on the page",
                "selector": "#mp-welcomecount",
                "value": "Wikipedia",
            },
            {
                # No selector — exercises Tier 2 observe() and subsequent cache hit
                "action": "click",
                "instruction": "Click on today's featured article link",
            },
        ],
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # Check if the database already has test cases — skip if so.
        result = await session.execute(select(TestCase))
        existing = result.scalars().all()
        if existing:
            print(
                f"  Database already contains {len(existing)} test case(s). "
                "Skipping seed — delete existing rows to re-seed."
            )
            return

        # Insert demo test cases.
        for tc_data in DEMO_TEST_CASES:
            session.add(TestCase(**tc_data))

        # Ensure a default ExecutionSettings row exists.
        settings_result = await session.execute(select(ExecutionSettings))
        if settings_result.scalar_one_or_none() is None:
            session.add(
                ExecutionSettings(
                    fallback_strategy="option_c",
                    timeout_per_tier_seconds=10,
                    max_retry_per_tier=2,
                )
            )

        await session.commit()

    print(f"  Seeded {len(DEMO_TEST_CASES)} demo test cases with default 'option_c' settings.")
    print()
    print("  Open http://localhost:5173 → Tests page to see them, or run one from the Run page.")


if __name__ == "__main__":
    asyncio.run(seed())
