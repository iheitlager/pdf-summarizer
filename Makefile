# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

VENV := .venv
PYTHON_VERSION := 3.13
MAIN_MODULE := src/pdf_summarizer/main.py
LOCAL_DOMAIN := pdf-summarizer.local

.PHONY: env install install-dev test help clean run lint format type-check check
.PHONY: start stop cleanup build rebuild run-docker logs shell down docker-clean
.PHONY: sbom audit sbom-check

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
	@mkdir -p data/logs
	@mkdir -p data/uploads
	@mkdir -p data/db
	@if [ ! -f uv.lock ]; then \
			echo "No uv.lock found, generating lock file..."; \
			uv lock; \
		fi
	@uv run python -c "import pdf_summarizer; print(f'pdf_summarizer version: {pdf_summarizer.__version__}')"
	@echo "To activate: source $(VENV)/bin/activate"

sync: ## Sync dependencies into the virtual environment
	@echo "Syncing dependencies into virtual environment..."
	uv sync > /dev/null
	uv sync --group dev > /dev/null
	@echo "✓ Dependencies synced"

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
	@rm -rf data/logs/
	@rm -rf data/uploads/
	@rm -rf data/db/
	@rm -rf .ssl-certs/
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
## SBOM & Security Commands
## ===================================

sbom: ## Generate Software Bill of Materials (SBOM)
	@echo "Generating SBOM..."
	@uv pip freeze > requirements.txt
	@uv run cyclonedx-py requirements requirements.txt -o sbom.json --of JSON
	@rm requirements.txt
	@echo "✓ SBOM generated: sbom.json"

audit: ## Run security vulnerability audit
	@echo "Running security audit..."
	@uv run pip-audit --desc
	@echo "✓ Security audit complete"

sbom-check: ## Generate SBOM and run security audit
	@echo "Running comprehensive SBOM and security check..."
	@uv pip freeze > requirements.txt
	@uv run cyclonedx-py requirements requirements.txt -o sbom.json --of JSON
	@echo "✓ SBOM generated: sbom.json"
	@uv run pip-audit --format json --output security-report.json
	@echo "✓ Security report: security-report.json"
	@rm requirements.txt
	@echo "✓ SBOM check complete"

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

.ssl-certs/nginx.crt: # Create self-signed SSL certificates
	@mkdir -p .ssl-certs
	@mkcert -key-file .ssl-certs/nginx.key -cert-file .ssl-certs/nginx.crt \
		$(LOCAL_DOMAIN) \
		localhost \
		127.0.0.1 \
		*.$(LOCAL_DOMAIN)

cleanup: ## Clean up Docker resources
	@echo "Cleaning up Docker resources..."
	@docker images | grep "localhost:" | awk '{print $$3}' | xargs docker rmi -f 2>/dev/null || true
	@docker rm -f $$(docker ps -aq) 2>/dev/null || true
	@docker rmi -f $$(docker images -aq) 2>/dev/null || true
	@docker volume prune -f 2>/dev/null || true
	@docker network prune -f 2>/dev/null || true
	@docker system prune -a -f --volumes 2>/dev/null || true
	@echo "✓ Docker cleanup completed"

up: .ssl-certs/nginx.crt ## Build pdf-summarizer container
	@echo "Building pdf-summarizer container..."
	@if ! grep -q "$(LOCAL_DOMAIN)" /etc/hosts; then \
		echo "127.0.0.1 $(LOCAL_DOMAIN)" | sudo tee -a /etc/hosts; \
	fi
	@mkdir -p data/db data/uploads data/logs
	docker-compose -f docker-compose.yml up  --build -d
	@echo "✓ Container built and started"
	@echo "Access the application at http://localhost:8000"

rebuild: ## Force rebuild without cache and restart
	@echo "Rebuilding pdf-summarizer without cache..."
	@mkdir -p data/db data/uploads data/logs
	docker-compose -f docker-compose.yml build --no-cache pdf-summarizer-1 pdf-summarizer-1
	docker-compose -f docker-compose.yml up -d
	@echo "✓ Container rebuilt and restarted"

logs: ## View container logs
	@echo "Viewing container logs (Ctrl+C to exit)..."
	docker-compose -f docker-compose.yml logs -f

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