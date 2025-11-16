VENV := .venv
PYTHON_VERSION := 3.13
MAIN_MODULE := src/pdf_summarizer/main.py

.PHONY: env install install-dev test help clean run lint format type-check check


check:
	@echo "Checking for required tools..."
	@command -v uv >/dev/null 2>&1 || { echo >&2 "✗ 'uv' is required but not installed. Please install it from https://github.com/astral-sh/uv"; exit 1; }
	@uv run ruff --version > /dev/null 2>&1 || { echo >&2 "✗ ruff is not installed"; exit 1; }
	@uv run black --version > /dev/null 2>&1 || { echo >&2 "✗ black is not installed"; exit 1; }
	@uv run mypy --version > /dev/null 2>&1 || { echo >&2 "✗ mypy is not installed"; exit 1; }
	@echo "✓ All required tools are installed"

help:
	@echo "Available targets:"
	@echo "  make check       - Verify all required tools are installed"
	@echo "  make env         - Create virtual environment and install all dependencies"
	@echo "  make run         - Run the application"
	@echo "  make lint        - Check code with ruff linter"
	@echo "  make format      - Format code with black and ruff"
	@echo "  make type-check  - Check types with mypy"
	@echo "  make test        - Run tests with pytest and generate coverage report"
	@echo "  make clean       - Remove virtual environment and Python build files"

env:
	@echo "✓ Setting up development environment with Python $(PYTHON_VERSION)..."
	uv venv $(VENV) --python $(PYTHON_VERSION) --clear > /dev/null
	@echo "✓ Virtual environment created at $(VENV)/"
	uv pip install --python $(VENV)/bin/python -e . >/dev/null
	uv pip install --python $(VENV)/bin/python -e ".[dev]" >/dev/null
	@mkdir -p logs
	@mkdir -p uploads
	@echo "To activate: source $(VENV)/bin/activate"

test:
	@echo "Running tests with coverage..."
	@pytest
	@echo "✓ Tests completed. Coverage report generated in htmlcov/index.html"

lint:
	@echo "Linting code with ruff..."
	uv run ruff check src/ tests/
	@echo "✓ Linting passed"

format:
	@echo "Formatting code with black..."
	uv run black src/ tests/
	@echo "Formatting and fixing with ruff..."
	uv run ruff check --fix src/ tests/
	@echo "✓ Code formatted"

type-check:
	@echo "Type checking with mypy..."
	uv run mypy src/
	@echo "✓ Type checking passed"

clean:
	@echo "Cleaning up..."
	@rm -rf $(VENV)
	@rm -rf .env
	@rm -rf logs
	@rm -rf uploads/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name ".coverage" -delete
	@echo "✓ Cleaned up successfully"

run:
	@echo "Starting application..."
	uv run python -m pdf_summarizer.main

.DEFAULT_GOAL := help
