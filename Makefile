# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

VENV := .venv
PYTHON_VERSION := 3.13
MAIN_MODULE := src/pdf_summarizer/main.py

.PHONY: env install install-dev test help clean run lint format type-check check
.PHONY: start stop cleanup build rebuild run-docker logs shell down docker-clean

version: ## Show project version
	@uv run python -c "import pdf_summarizer; print(f'pdf_summarizer version: {pdf_summarizer.__version__}')"

check: ## Verify required tooling is available
	@echo "Checking for required tools..."
	@command -v uv >/dev/null 2>&1 || { echo >&2 "✗ 'uv' is required but not installed. Please install it from https://github.com/astral-sh/uv"; exit 1; }
	@uv run ruff --version > /dev/null 2>&1 || { echo >&2 "✗ ruff is not installed"; exit 1; }
	@uv run black --version > /dev/null 2>&1 || { echo >&2 "✗ black is not installed"; exit 1; }
	@uv run mypy --version > /dev/null 2>&1 || { echo >&2 "✗ mypy is not installed"; exit 1; }
	@echo "✓ All required tools are installed"

env: ## Create and populate the development virtual environment
	@echo "✓ Setting up development environment with Python $(PYTHON_VERSION)..."
	uv venv $(VENV) --python $(PYTHON_VERSION) --clear > /dev/null
	@echo "✓ Virtual environment created at $(VENV)/"
	@uv sync  > /dev/null
	@uv sync --group dev  > /dev/null
	@mkdir -p logs
	@mkdir -p uploads
	@if [ ! -f uv.lock ]; then \
			echo "No uv.lock found, generating lock file..."; \
			uv lock; \
		fi
	@uv run python -c "import pdf_summarizer; print(f'pdf_summarizer version: {pdf_summarizer.__version__}')"
	@echo "To activate: source $(VENV)/bin/activate"

settings: ## Create configuration settings .env
	@echo "Creating settings"
	@env.sh -i .env.example

lock: ## Lock dependencies into uv.lock
	@echo "Locking dependencies..."
	uv lock

test: ## Run unit test suite with coverage
	@echo "Running tests with coverage..."
	uv run pytest -v tests/
	@echo "✓ Tests completed. Coverage report generated in htmlcov/index.html"

lint: ## Lint source and tests with ruff
	@echo "Linting code with ruff..."
	uv run ruff check src/ tests/
	@echo "✓ Linting passed"

format: ## Format code with black then autofix with ruff
	@echo "Formatting code with black..."
	uv run black src/ tests/
	@echo "Formatting and fixing with ruff..."
	uv run ruff check --fix src/ tests/
	@echo "✓ Code formatted"

type-check: ## Run mypy type checks
	@echo "Type checking with mypy..."
	uv run mypy src/
	@echo "✓ Type checking passed"

clean: ## Remove virtualenv, artifacts, and caches
	@echo "Cleaning up..."
	@rm -rf $(VENV)
	@rm -rf logs
	@rm -rf uploads/
	@rm -rf instance/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name ".coverage" -delete
	@echo "✓ Cleaned up successfully"

run: ## Launch the Flask application via uv
	@echo "Starting application..."
	uv run python -m main

## ===================================
## Docker/Colima Commands
## ===================================

start: ## Start Colima if not already running
	@echo "Starting Colima..."
	@colima start 2>/dev/null || true
	@colima status

stop: cleanup ## Stop Colima and clean up
	@echo "Stopping Colima..."
	@colima stop

cleanup: ## Clean up Docker resources
	@echo "Cleaning up Docker resources..."
	@docker images | grep "localhost:" | awk '{print $$3}' | xargs docker rmi -f 2>/dev/null || true
	@docker rm -f $$(docker ps -aq) 2>/dev/null || true
	@docker rmi -f $$(docker images -aq) 2>/dev/null || true
	@docker volume prune -f 2>/dev/null || true
	@docker network prune -f 2>/dev/null || true
	@docker system prune -a -f --volumes 2>/dev/null || true
	@echo "✓ Docker cleanup completed"

up: ## Build pdf-summarizer container
	@echo "Building pdf-summarizer container..."
	@mkdir -p data/db data/uploads data/logs
	docker-compose -f docker-compose.yml up pdf-summarizer --build -d
	@echo "✓ Container built and started"
	@echo "Access the application at http://localhost:8000"

rebuild: ## Force rebuild without cache and restart
	@echo "Rebuilding pdf-summarizer without cache..."
	@mkdir -p data/db data/uploads data/logs
	docker-compose -f docker-compose.yml build --no-cache pdf-summarizer
	docker-compose -f docker-compose.yml up -d
	@echo "✓ Container rebuilt and restarted"

logs: ## View container logs
	@echo "Viewing container logs (Ctrl+C to exit)..."
	docker-compose -f docker-compose.yml logs -f pdf-summarizer

shell: ## Open shell in running container
	@echo "Opening shell in pdf-summarizer container..."
	docker-compose -f docker-compose.yml exec pdf-summarizer /bin/bash

down: ## Stop and remove containers
	@echo "Stopping containers..."
	docker-compose -f docker-compose.yml down
	@echo "✓ Containers stopped and removed"

docker-clean: down ## Stop containers and clean up volumes
	@echo "Removing Docker volumes..."
	@rm -rf data/db/* data/uploads/* data/logs/*
	@echo "✓ Volumes cleaned"

.DEFAULT_GOAL := help

help: ## Shows this help screen
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""