# Implementation Plan: 3-Tier Execution Engine (Lite Portfolio Edition)

## Overview

A focused, portfolio-quality reimplementation of the 3-tier browser execution engine from
[AI-Web-Test-v1](https://github.com/deencat/AI-Web-Test-v1). The lite version strips away the
multi-agent system, knowledge base and authentication machinery to put the core architectural
pattern — **cascading execution tiers with XPath caching** — front-and-centre for interview
discussions.

**What this demonstrates:**
- Systems thinking (when to use cheap fast paths vs expensive AI fall-backs)
- Async Python service design (FastAPI + Playwright)
- React frontend consuming a real streaming API
- Performance engineering (SHA-256 caching, lazy browser initialisation)
- Test automation domain knowledge

---

## Requirements

**Functional**
- Run a sequence of natural-language test steps against any public URL
- Automatically escalate from Playwright → XPath cache → Stagehand AI when a step fails
- Persist XPath cache entries across executions (SHA-256 keyed by instruction text)
- Three configurable fallback strategies (Option A / B / C)
- Execution history with per-step tier analytics
- Real-time progress stream (Server-Sent Events)

**Non-Functional**
- Self-contained: `sqlite` only, no external services required to run locally
- Single-command start (`docker compose up` or `make dev`)
- Tier 1 steps complete in < 500 ms (zero LLM calls)
- 90 %+ unit test coverage on the execution service layer

**Out of Scope (deliberately omitted from lite version)**
- Multi-agent pipeline (ObservationAgent / RequirementsAgent / EvolutionAgent)
- JWT authentication
- Knowledge base / document upload
- Kubernetes deployment
- PostgreSQL / Redis / Qdrant

---

## Architecture Changes from Original

| Original (full project)             | Lite version                          | Reason                         |
|-------------------------------------|---------------------------------------|--------------------------------|
| 68 + API endpoints                  | ~15 endpoints                         | Focus on core feature          |
| SQLAlchemy + PostgreSQL             | SQLAlchemy + SQLite                   | Zero-config local setup        |
| Real Stagehand npm package          | Stagehand via `subprocess` adapter    | Avoids Node/Python split setup |
| Multi-provider LLM (4 providers)    | Single provider (OpenRouter or Gemini)| Simplicity                     |
| Phase 3 agents                      | Removed entirely                      | Out of scope                   |
| React (no design system)            | React + shadcn/ui (Tailwind)           | Cleaner demo UI                |

---

## File Structure (Target)

```
3-tier-execution-engine/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── executions.py        # run, stream, list, get
│   │   │   ├── settings.py          # CRUD fallback strategy config
│   │   │   └── tests.py             # CRUD test cases
│   │   ├── core/
│   │   │   ├── config.py            # env-var settings (pydantic-settings)
│   │   │   └── database.py          # SQLAlchemy session factory
│   │   ├── models/
│   │   │   ├── test_case.py         # TestCase ORM model
│   │   │   ├── execution.py         # Execution + ExecutionStep ORM
│   │   │   ├── execution_settings.py
│   │   │   └── xpath_cache.py       # XPathCache ORM model
│   │   ├── schemas/
│   │   │   ├── test_case.py
│   │   │   ├── execution.py
│   │   │   └── settings.py
│   │   └── services/
│   │       ├── three_tier_service.py     # Main orchestrator
│   │       ├── tier1_playwright.py       # CSS / XPath direct
│   │       ├── tier2_hybrid.py           # observe() → XPath + cache
│   │       ├── tier3_stagehand.py        # Full AI act()
│   │       └── xpath_cache_service.py   # SHA-256 read/write cache
│   ├── tests/
│   │   ├── test_tier1.py
│   │   ├── test_tier2.py
│   │   ├── test_tier3.py
│   │   ├── test_three_tier_service.py
│   │   └── test_xpath_cache.py
│   ├── alembic/                          # DB migrations
│   ├── requirements.txt
│   ├── .env.example
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ExecutionSettings.tsx    # Option A/B/C picker
│   │   │   ├── StepEditor.tsx           # Plain-text step editor (one step per line; action: prefix optional)
│   │   │   ├── ExecutionProgress.tsx    # Live SSE progress view
│   │   │   ├── TierBadge.tsx            # Coloured badge: T1/T2/T3
│   │   │   └── TierAnalyticsChart.tsx  # Bar chart tier distribution
│   │   ├── pages/
│   │   │   ├── TestsPage.tsx
│   │   │   ├── RunPage.tsx
│   │   │   └── HistoryPage.tsx
│   │   ├── services/
│   │   │   └── api.ts                   # axios wrapper + SSE hook
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── Makefile
└── README.md                            # Portfolio case-study (existing)
```

---

## Implementation Steps

### Phase 1 — Project Scaffold & Data Models (Day 1-2)

**Goal:** Both servers start; SQLite DB created; empty API returns 200.

1. **Backend scaffold** (File: `backend/main.py`, `backend/app/core/config.py`)
   - Action: Init FastAPI app, CORS for `localhost:5173`, mount `/api/v1` router, `/health` endpoint
   - Why: Everything else routes through this entry point
   - Dependencies: None
   - Risk: Low

2. **Database setup + migrations** (File: `backend/app/core/database.py`, `backend/alembic/`)
   - Action: SQLAlchemy async engine pointing at `sqlite+aiosqlite:///./engine.db`; Alembic init; initial migration
   - Why: All services depend on DB models existing
   - Dependencies: Step 1
   - Risk: Low — SQLite has no server to configure

3. **ORM models** (File: `backend/app/models/*.py`)
   - Action: Create four models:
     - `TestCase(id, title, url, steps: JSON, created_at)`
     - `Execution(id, test_case_id, strategy, status, started_at, finished_at)`
     - `ExecutionStep(id, execution_id, index, instruction, tier_used, success, duration_ms, error, xpath_cached)`
     - `ExecutionSettings(id, fallback_strategy, timeout_per_tier_seconds, max_retry_per_tier)`
     - `XPathCache(id, instruction_hash, url_pattern, xpath, hit_count, created_at, last_used_at)`
   - Why: These are the persistence contracts for all five services
   - Dependencies: Step 2
   - Risk: Low

4. **Pydantic schemas** (File: `backend/app/schemas/*.py`)
   - Action: Request/response models for each resource; add `model_config = ConfigDict(from_attributes=True)`
   - Why: FastAPI validation + OpenAPI docs generation
   - Dependencies: Step 3
   - Risk: Low

5. **Frontend scaffold** (File: `frontend/`)
   - Action: `npm create vite@latest frontend -- --template react-ts`; install `shadcn/ui`, `axios`, `recharts`, `react-router-dom`; proxy `/api` → `localhost:8000` in `vite.config.ts`
   - Why: Dev server with hot reload and proxy avoids CORS during development
   - Dependencies: None (parallel with backend steps)
   - Risk: Low

---

### Phase 2 — Core Execution Engine (Day 3-6)

**Goal:** `three_tier_service.execute_step()` returns correct tier result for mocked steps; all unit tests pass.

6. **XPath cache service** (File: `backend/app/services/xpath_cache_service.py`)
   - Action:
     - `get(instruction: str, page_url: str) -> Optional[str]` — hash instruction with SHA-256, query DB, bump `hit_count`
     - `store(instruction, page_url, xpath)` — upsert cache row
     - URL normalisation: strip query params before matching
   - Why: Cache is the performance multiplier — Tier 2 cache hits cost ~$0 LLM
   - Dependencies: Step 3 (XPathCache model)
   - Risk: Low — pure DB operations

7. **Tier 1 — Playwright direct executor** (File: `backend/app/services/tier1_playwright.py`)
   - Action:
     - `execute_step(page, step) -> TierResult`
     - Extract `selector` field from step; call `page.locator(selector).click()` / `.fill()` / `.goto()` based on `action`
     - Wrap in `asyncio.wait_for(…, timeout)` → return structured `TierResult(tier=1, success, duration_ms, error)`
     - Support actions: `navigate`, `click`, `fill`, `press`, `assert_text`, `assert_url`
   - Why: 85 % of steps should succeed here at zero LLM cost
   - Dependencies: Step 6
   - Risk: Medium — Playwright async API has subtle timeout/frame handling

8. **Tier 2 — Hybrid XPath executor** (File: `backend/app/services/tier2_hybrid.py`)
   - Action:
     - Cache-first: call `xpath_cache.get(instruction, url)` — if hit, execute with Playwright `page.locator(f"xpath={xpath}")`
     - Cache miss: call `stagehand.observe(instruction)` to extract live XPath from DOM — store result in cache — execute via Playwright
     - Return `TierResult(tier=2, success, duration_ms, xpath_cached=True/False)`
   - Why: Cache hits make Tier 2 nearly as fast as Tier 1 after warm-up
   - Dependencies: Steps 6, 7
   - Risk: Medium — Stagehand `observe()` interop requires the Node adapter

9. **Tier 3 — Stagehand AI executor** (File: `backend/app/services/tier3_stagehand.py`)
   - Action:
     - Call `stagehand.act(instruction)` — full LLM reasoning
     - Return `TierResult(tier=3, success, duration_ms, error)`
   - Why: Last-resort fallback; handles dynamic/obscured elements
   - Dependencies: Step 8
   - Risk: Medium — LLM latency (10-30 s expected); needs API key

10. **Stagehand Python adapter** (File: `backend/app/services/stagehand_adapter.py`)
    - Action: Thin wrapper that launches Stagehand via CDP (Playwright creates Chromium; Stagehand attaches via `cdp_endpoint`). Expose `observe(instruction) -> str` and `act(instruction) -> bool`. Fall back to a `MockStagehand` mode (env var `STAGEHAND_MOCK=true`) that returns canned data — this lets the project run without an LLM API key for CI.
    - Why: Decouples the Stagehand dependency; mock mode critical for CI and demo resilience
    - Dependencies: None
    - Risk: High — bridging Node.js Stagehand with Python Playwright is the hardest integration. **Mitigation:** Start with the mock adapter; add real adapter incrementally.

11. **Three-tier orchestrator** (File: `backend/app/services/three_tier_service.py`)
    - Action:
      - Accept `(page, step, settings, execution_id, step_index)` — attempt Tier 1 always
      - On Tier 1 failure, branch on `settings.fallback_strategy`:
        - `option_a`: Tier 1 → Tier 2
        - `option_b`: Tier 1 → Tier 3
        - `option_c`: Tier 1 → Tier 2 → Tier 3
      - Collect `execution_history: List[TierResult]`, persist `ExecutionStep` row after each step
      - Emit progress event via asyncio `Queue` (consumed by SSE endpoint)
    - Why: This is the portfolio centrepiece — the strategy pattern implementation
    - Dependencies: Steps 7, 8, 9
    - Risk: Medium — async browser lifecycle needs careful cleanup

12. **Unit tests for execution services** (File: `backend/tests/`)
    - Action: Mock `page` (use `AsyncMock`), mock Stagehand adapter; test:
      - Tier 1 success path
      - Tier 1 fail → Tier 2 cache hit (Option A)
      - Tier 1 fail → Tier 2 cache miss → Tier 3 (Option C)
      - XPath cache SHA-256 keying
      - `option_b` skip-Tier-2 path
    - Why: Demonstrates TDD discipline; makes the logic verifiable without a real browser
    - Dependencies: Steps 6-11
    - Risk: Low

---

### Phase 3 — REST API Layer (Day 7-8)

**Goal:** All endpoints return correct data; Swagger UI is usable.

13. **Tests CRUD endpoints** (File: `backend/app/api/tests.py`)
    - Action: `POST /api/v1/tests`, `GET /api/v1/tests`, `GET /api/v1/tests/{id}`, `PUT`, `DELETE`
    - Step schema: `[{ "action": "click|fill|navigate|assert_text|assert_url", "instruction": "...", "selector": "optional-css", "value": "optional" }]`
    - Why: Frontend needs to create and manage test cases
    - Dependencies: Steps 3, 4
    - Risk: Low

14. **Execution endpoints + SSE stream** (File: `backend/app/api/executions.py`)
    - Action:
      - `POST /api/v1/executions` — start execution, return `execution_id` immediately
      - `GET /api/v1/executions/{id}/stream` — SSE endpoint yielding `TierResult` events as JSON lines
      - `GET /api/v1/executions` — history list with aggregated stats
      - `GET /api/v1/executions/{id}` — detail with all steps
    - SSE event shape: `data: {"step_index": 0, "tier": 1, "success": true, "duration_ms": 48}\n\n`
    - Why: Real-time progress makes the demo visually compelling
    - Dependencies: Steps 11, 13
    - Risk: Medium — SSE lifecycle (client disconnect cleanup, asyncio task cancellation)

15. **Settings endpoint** (File: `backend/app/api/settings.py`)
    - Action: `GET /api/v1/settings`, `PUT /api/v1/settings` — upsert single settings row
    - Why: Frontend settings panel persists strategy choice
    - Dependencies: Step 3
    - Risk: Low

---

### Phase 4 — Frontend UI (Day 9-12)

**Goal:** Usable React app that runs a test and shows which tier each step used.

16. **API service layer** (File: `frontend/src/services/api.ts`)
    - Action: Axios wrapper with base URL; typed functions for all 15 endpoints; `useSSE(executionId)` hook using `EventSource`
    - Dependencies: Step 14
    - Risk: Low

17. **Tests page** (File: `frontend/src/pages/TestsPage.tsx`)
    - Action: List test cases; "New Test" button and per-card "Edit" button both open the same shared modal form; title + URL fields; plain-text `StepEditor`; "Create" / "Save" button submits to the appropriate API call
    - Key component `StepEditor`: single `<textarea>` — one step per line in plain text. Action can be optionally prefixed (`navigate: …`, `fill: …`); bare lines default to `click`. Parses to/from `TestStep[]` automatically.
    - Edit flow: clicking "Edit" on a card pre-populates the modal and calls `PUT /api/v1/tests/{id}` on save; modal heading changes to "Edit Test Case"
    - Dependencies: Steps 13, 16
    - Risk: Low

18. **Run page with live progress** (File: `frontend/src/pages/RunPage.tsx`)
    - Action:
      - "Run Test" button → `POST /executions` → opens SSE stream
      - `ExecutionProgress.tsx`: vertical timeline; each step card shows spinner → tier badge on completion
      - `TierBadge.tsx`: `T1` green / `T2` amber / `T3` red (cost indicator)
      - Summary bar: X steps, Y ms total, Z% Tier 1
    - Why: This is the centrepiece UI the interviewer will see
    - Dependencies: Steps 14, 16, 17
    - Risk: Medium — SSE reconnection edge cases

19. **Execution history page** (File: `frontend/src/pages/HistoryPage.tsx`)
    - Action:
      - Table of past executions: test name, date, strategy, pass/fail, step count
      - Click row → detail view with per-step tier breakdown
      - `TierAnalyticsChart.tsx`: stacked bar chart (recharts) showing Tier 1 / Tier 2 / Tier 3 step distribution per execution
    - Why: Demonstrates the cost-efficiency story visually (most bars should be green/T1)
    - Dependencies: Steps 14, 16
    - Risk: Low

20. **Execution settings panel** (File: `frontend/src/components/ExecutionSettings.tsx`)
    - Action: Three radio cards — Option A / B / C — each showing a diagram of the fallback flow, success-rate estimate, and cost profile. Persists via `PUT /api/v1/settings`.
    - Why: Directly mirrors the settings UI in the original project (a talking point in interviews)
    - Dependencies: Step 15, 16
    - Risk: Low

---

### Phase 5 — Demo Polish & Documentation (Day 13-14)

**Goal:** One-command setup; recorded demo runs cleanly; README is investor/interviewer ready.

21. **Docker Compose** (File: `docker-compose.yml`)
    - Action: Two services — `backend` (Python 3.12, installs Playwright Chromium) and `frontend` (Node 20, Vite preview build). Shared volume for SQLite DB.
    - Why: Removes "works on my machine" risk for demos and recruiters cloning the repo
    - Dependencies: All prior steps
    - Risk: Medium — Playwright Chromium add ~500 MB to image; use `mcr.microsoft.com/playwright/python` base image

22. **Makefile** (File: `Makefile`)
    - Action: Targets: `make dev` (both servers), `make test` (pytest + vitest), `make demo` (seed DB + open browser)
    - Dependencies: All prior steps
    - Risk: Low

23. **Demo seed script** (File: `backend/seed_demo.py`)
    - Action: Insert 2-3 pre-built test cases targeting stable public URLs (e.g. `https://example.com`, `https://playwright.dev`) with a mix of steps that exercise all three tiers
    - Why: Interviewer can run `make demo` and immediately see the tier cascade in action without creating data manually
    - Dependencies: Step 3
    - Risk: Low — targets must be stable public pages

24. **Update README** (File: `README.md`)
    - Action: Add "Getting Started" section (prerequisites, `make dev`, `.env` keys), architecture diagram (the existing ASCII art), and a "How it works" section walking through the tier cascade with code snippets
    - Dependencies: All prior steps
    - Risk: Low

---

## Testing Strategy

### Unit Tests (pytest + AsyncMock)
- `test_tier1.py` — selector success, timeout, unsupported action
- `test_tier2.py` — cache hit path, cache miss → observe() path, store() called once
- `test_tier3.py` — act() success, act() failure, mock adapter fallback
- `test_three_tier_service.py` — all three option flows (A/B/C), mid-run failure propagation
- `test_xpath_cache.py` — SHA-256 keying, URL normalisation, hit_count increment

### Integration Tests (pytest + real Playwright)
- `test_integration_e2e.py` — run a 3-step test against `https://example.com` with Option C; assert Tier 1 handles all steps (no LLM calls needed for a simple static page)

### Frontend Tests (vitest + testing-library)
- `TierBadge.test.tsx` — renders correct colour per tier
- `ExecutionSettings.test.tsx` — radio selection persists correctly
- `api.test.ts` — mock axios responses for CRUD and SSE hook

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Stagehand Node↔Python bridge is fragile | Ship `MockStagehand` adapter by default; real adapter is opt-in via `STAGEHAND_ENABLED=true`. All tiers unit-testable without real Stagehand. |
| LLM API key required for Tier 3 | `STAGEHAND_MOCK=true` plus `OPENROUTER_API_KEY=demo` fallback in seed script so demo runs without a paid key |
| Playwright Chromium install in CI | Use `mcr.microsoft.com/playwright/python:v1.44.0-jammy` base image; cache `~/.cache/ms-playwright` |
| SQLite concurrency during SSE streaming | Use `check_same_thread=False` + single async session per request; no write concurrency issues at demo scale |
| Frontend SSE reconnection on tab sleep | Implement 3-second reconnect backoff in `useSSE` hook |

---

## Success Criteria

- [ ] `make dev` starts both servers from a clean clone in < 2 minutes
- [ ] Running a 5-step test against `https://example.com` shows ≥ 4 steps passing at Tier 1 (green badges)
- [ ] Changing strategy to Option A and running a step with a broken selector shows Tier 2 kick in
- [ ] XPath cache hit is visible in Execution detail (badge: "T2 cached")
- [ ] Tier analytics chart shows correct distribution
- [ ] All unit tests pass: `make test`
- [ ] Swagger UI (`/docs`) documents all 15 endpoints
- [ ] Docker Compose builds and `make demo` opens the running app in a browser

---

## Sprint Schedule (2-week solo)

| Day | Focus | Deliverable |
|-----|-------|-------------|
| 1-2 | Phase 1 | Backend boots, DB migrates, frontend scaffolded |
| 3-4 | Phase 2 (services) | XPath cache + Tier 1 + unit tests passing |
| 5-6 | Phase 2 (cont) | Tier 2 + Tier 3 + orchestrator + mock adapter |
| 7-8 | Phase 3 | All 15 REST endpoints + SSE stream |
| 9-10 | Phase 4 (frontend) | Tests page + run page with live progress |
| 11-12 | Phase 4 (cont) | History page + analytics chart + settings panel |
| 13 | Phase 5 | Docker Compose + Makefile + seed script |
| 14 | Phase 5 (cont) | README polish + recorded demo GIF |

---

## Interview Talking Points (Pre-built)

Once built, the project surfaces these discussion areas naturally:

| Interviewer asks… | Point to… |
|---|---|
| "Walk me through a design decision" | The 3-tier cascade — trade-off between speed/cost and reliability |
| "How did you handle shared state in async Python?" | Browser instance lifecycle in orchestrator — Playwright page shared across tiers |
| "How does the caching work?" | SHA-256 on instruction text, URL-pattern normalisation, `hit_count` analytics |
| "How would you scale this?" | Mock → Redis cache, SQLite → PostgreSQL, single process → Celery workers |
| "How do you test browser automation code?" | `MockStagehand` adapter pattern — unit-testable without a real browser |
| "What would you add next?" | Tier 2 XPath freshness TTL, self-healing (re-observe on stale cache), Phase 3 multi-agent |
