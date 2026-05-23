.PHONY: help setup backend frontend dev test test-backend test-frontend migrate seed

BACKEND_DIR := backend
FRONTEND_DIR := frontend
PYTHON      := $(BACKEND_DIR)/.venv/bin/python
PIP         := $(BACKEND_DIR)/.venv/bin/pip
PYTEST      := $(BACKEND_DIR)/.venv/bin/pytest
ALEMBIC     := $(BACKEND_DIR)/.venv/bin/alembic

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*##"}; {printf "  %-18s %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────────────────────────────

setup: setup-backend setup-frontend  ## Install all dependencies

setup-backend:  ## Create Python 3.12 venv and install dependencies
	python3.12 -m venv $(BACKEND_DIR)/.venv
	$(PIP) install --upgrade pip -q
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt -q
	cp -n $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env 2>/dev/null || true

setup-frontend:  ## Install npm dependencies
	cd $(FRONTEND_DIR) && npm install

# ── Database ───────────────────────────────────────────────────────────────

migrate:  ## Apply Alembic migrations
	cd $(BACKEND_DIR) && $(ALEMBIC) upgrade head

# ── Development servers ────────────────────────────────────────────────────

backend:  ## Start FastAPI dev server (port 8000)
	cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn main:app --reload --port 8000

frontend:  ## Start Vite dev server (port 5173)
	cd $(FRONTEND_DIR) && npm run dev

dev:  ## Start both servers in parallel
	@echo "Starting backend on :8000 and frontend on :5173 ..."
	@$(MAKE) -j2 backend frontend

# ── Tests ──────────────────────────────────────────────────────────────────

test-backend:  ## Run backend pytest with coverage
	cd $(BACKEND_DIR) && $(PYTEST) -q

test-frontend:  ## Run vitest
	cd $(FRONTEND_DIR) && npm test

test: test-backend test-frontend  ## Run all tests

# ── Demo ───────────────────────────────────────────────────────────────────

demo: migrate  ## Seed DB with demo data and open browser
	cd $(BACKEND_DIR) && $(PYTHON) seed_demo.py
	@echo "Backend: http://localhost:8000/docs"
	@echo "Frontend: http://localhost:5173"
	@$(MAKE) -j2 backend frontend
