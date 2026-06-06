.PHONY: install test test-cov lint format typecheck up down clean frontend-install frontend-dev

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3.11 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

test:
	$(VENV)/bin/pytest

acceptance:
	$(VENV)/bin/pytest tests/acceptance -v

validate:
	$(VENV)/bin/python -m cdmas.validator

test-cov:
	$(VENV)/bin/pytest --cov=cdmas --cov-report=term-missing --cov-report=html

lint:
	$(VENV)/bin/ruff check src tests

format:
	$(VENV)/bin/ruff format src tests
	$(VENV)/bin/ruff check --fix src tests

typecheck:
	$(VENV)/bin/mypy

up:
	docker compose up --build

down:
	docker compose down -v

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
