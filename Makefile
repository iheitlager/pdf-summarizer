VENV := .venv
PYTHON_VERSION := 3.13
MAIN_MODULE := src/pdf_summarizer/main.py

.PHONY: env install install-dev test help clean run

help:
	@echo "Available targets:"
	@echo "  make env         - Create virtual environment and install all dependencies"
	@echo "  make run         - Run the application (requires activated venv)"
	@echo "  make test        - Run tests with pytest and generate coverage report"
	@echo "  make clean       - Remove virtual environment and Python build files"

env:
	@echo "✓ Setting up development environment with Python $(PYTHON_VERSION)..."
	uv venv $(VENV) --python $(PYTHON_VERSION) --clear > /dev/null
	@echo "✓ Virtual environment created at $(VENV)/"
	uv pip install --python $(VENV)/bin/python -e . >/dev/null
	uv pip install --python $(VENV)/bin/python -e ".[dev]" >/dev/null
	@echo "To activate: source $(VENV)/bin/activate"

test:
	@echo "Running tests with coverage..."
	pytest
	@echo "✓ Tests completed. Coverage report generated in htmlcov/index.html"

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	rm -rf .env
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	@echo "✓ Cleaned up successfully"

run:
	@echo "Starting application..."
	. $(VENV)/bin/activate && python -m pdf_summarizer.main

.DEFAULT_GOAL := help
