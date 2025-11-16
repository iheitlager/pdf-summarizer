# Claude Development Guide for PDF Summarizer

This document provides essential guidelines and instructions for Claude (AI assistant) when working on the PDF Summarizer project.

## Project Overview

**PDF Summarizer** is a Flask web application that uploads PDF files and generates AI-powered summaries using Anthropic's Claude API. The project includes caching, session management, rate limiting, comprehensive logging, and automated cleanup features.

- **Language**: Python 3.13
- **Framework**: Flask
- **Package Manager**: `uv` (REQUIRED - see below)
- **Database**: SQLite with SQLAlchemy ORM
- **Testing**: pytest with 90%+ coverage
- **License**: Apache 2.0

## Critical Rules

### 1. Version Management (MANDATORY)

**ALWAYS keep versions synchronized in THREE places:**

1. `src/pdf_summarizer/__init__.py` - `__version__ = "x.y.z"`
2. `README.md` - Line 3: `**Version**: x.y.z | [Changelog](./CHANGELOG.md)`
3. `CHANGELOG.md` - Top section with version number and date

**Before any version bump:**
- Update all three locations with the SAME version number
- Follow [Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH
- Add changelog entry with date in YYYY-MM-DD format

**Version bump guidelines:**
- PATCH (0.0.x): Bug fixes, small improvements, documentation
- MINOR (0.x.0): New features, backward-compatible changes
- MAJOR (x.0.0): Breaking changes, major refactoring

### 2. Package Manager: Always Use `uv`

**CRITICAL: This project has a local `.venv` and MUST use `uv` for all operations.**

**Always use `uv` commands:**
```bash
# CORRECT - Using uv
uv run pytest
uv run python -m pdf_summarizer.main
uv run ruff check .
uv run black .
uv run mypy src/

# INCORRECT - Don't use these
pytest
python -m pdf_summarizer.main
pip install something
```

**Virtual environment setup:**
```bash
# Create/recreate environment
make env

# Or manually
uv venv .venv --python 3.13
uv pip install -e .
uv pip install -e ".[dev]"
```

### 3. Makefile Commands

Use these commands for common tasks:

```bash
make help         # Show all available commands
make env          # Set up complete dev environment
make test         # Run test suite with coverage
make run          # Run the application
make lint         # Check code with ruff
make format       # Format with black and ruff
make type-check   # Type check with mypy
make clean        # Remove venv and build artifacts
```

## Development Workflow

### Making Changes

1. **Before starting:**
   - Ensure `.venv` exists: `make env`
   - Understand the change scope (bug fix vs feature)
   - Check if version bump is needed

2. **During development:**
   - Write code following project conventions
   - Add/update tests in `tests/` directory
   - Run `make lint` and `make format` regularly
   - Keep test coverage above 90%

3. **Before committing:**
   - Run `make test` - ALL tests must pass
   - Run `make format` - Code must be formatted
   - Run `make type-check` - Type checks should pass
   - Update CHANGELOG.md if needed
   - Update version in all 3 places if needed

### Adding New Features

When adding new features:

1. **Update tests first (TDD approach):**
   - Add test file(s) in `tests/`
   - Use existing fixtures from `tests/conftest.py`
   - Aim for comprehensive coverage

2. **Implement the feature:**
   - Add code in appropriate module under `src/pdf_summarizer/`
   - Follow existing patterns and conventions
   - Add type hints where possible

3. **Update documentation:**
   - Add to CHANGELOG.md under appropriate section (Added/Changed/Fixed)
   - Update README.md if user-facing
   - Add docstrings to new functions/classes

4. **Version bump:**
   - Determine appropriate version (PATCH/MINOR/MAJOR)
   - Update all three version locations
   - Add dated entry to CHANGELOG.md

## Testing Guidelines

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
uv run pytest tests/test_helpers.py

# Run specific test class
uv run pytest tests/test_routes.py::TestIndexRoute

# Run specific test function
uv run pytest tests/test_caching.py::test_cache_hit

# Verbose output
uv run pytest -v

# Coverage report
uv run pytest --cov=. --cov-report=term-missing --cov-report=html
```

### Test Structure

- **conftest.py**: 20+ fixtures for mocking, databases, PDFs, logging
- **Unit tests**: `test_helpers.py`, `test_models.py`, `test_forms.py`
- **Integration tests**: `test_routes.py`, `test_error_handlers.py`
- **Feature tests**: `test_caching.py`, `test_session.py`, `test_cleanup.py`, `test_logging.py`
- **E2E tests**: `test_integration.py`

### Writing Tests

- Use in-memory SQLite databases (provided by fixtures)
- Mock Anthropic API calls (use `mock_anthropic_response` fixture)
- Generate test PDFs dynamically (use PDF generator fixtures)
- Test both success and error paths
- Maintain 90%+ coverage

## Code Quality Standards

### Formatting and Linting

```bash
# Format code (required before commit)
make format

# Check linting
make lint

# Type checking
make type-check
```

### Code Style

- **Line length**: 100 characters (configured in black/ruff)
- **Python version**: 3.13
- **Imports**: Sorted with isort (via ruff)
- **Type hints**: Use where possible, but not required everywhere
- **Docstrings**: Add to all public functions/classes

### File Headers

All Python source files must include copyright and license:

```python
# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0
```

## Project Structure

```
.
├── src/pdf_summarizer/          # Main application package
│   ├── __init__.py              # VERSION LOCATION #1
│   ├── main.py                  # Flask app entry point
│   ├── models.py                # Database models (Upload, Summary)
│   ├── config.py                # Centralized configuration
│   ├── logging_config.py        # Logging setup
│   ├── utils.py                 # Utility functions
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── results.html
│   │   └── errors/
│   └── static/                  # CSS, JS, assets
├── tests/                       # Test suite (90%+ coverage)
│   ├── conftest.py              # Pytest fixtures
│   └── test_*.py                # Test modules
├── docs/                        # Documentation
│   └── database.md              # Database schema reference
├── pyproject.toml               # Dependencies and config
├── Makefile                     # Build automation
├── README.md                    # VERSION LOCATION #2
├── CHANGELOG.md                 # VERSION LOCATION #3
├── .env.example                 # Environment template
└── CLAUDE.md                    # This file
```

## Environment Variables

Key environment variables (see `.env.example`):

```bash
ANTHROPIC_API_KEY=your-key-here   # Required: Claude API key
SECRET_KEY=your-secret-key        # Required: Flask secret
LOG_LEVEL=INFO                    # Optional: Logging level
RETENTION_DAYS=30                 # Optional: Upload retention
CLEANUP_HOUR=3                    # Optional: Daily cleanup time
```

## Database Work

### Understanding the Schema

The database schema is fully documented in [docs/database.md](docs/database.md). Read this file to understand:
- Table structure and columns
- Relationships and foreign keys
- Indexes and constraints
- Caching mechanism
- Common query patterns

**Database Models Location**: [src/pdf_summarizer/models.py](src/pdf_summarizer/models.py)

### Making Schema Changes

When modifying the database schema:

1. **Update the model** in `src/pdf_summarizer/models.py`
2. **Update docs/database.md** with the new schema details
3. **Create migration** (for production deployments):
   ```bash
   flask db migrate -m "Description of change"
   flask db upgrade
   ```
4. **Update tests** in `tests/test_models.py`
5. **Update CHANGELOG.md** under "Changed" or "Added"
6. **Bump version** if schema change is significant

### Adding a New Table

1. Define model in `src/pdf_summarizer/models.py` (after existing models)
2. Add relationships if needed
3. Document in `docs/database.md` with full details
4. Create test file `tests/test_new_model.py`
5. Run `make test` to ensure all tests pass
6. Update CHANGELOG.md

### Database Queries

When writing database queries:
- Use indexed columns (`file_hash`, `session_id`) for filters
- Use `.first()` for single results
- Use `.limit()` for large result sets
- Use `db.joinedload()` to avoid N+1 queries
- Always handle `None` results from queries

Example:
```python
# Good - using index
upload = Upload.query.filter_by(file_hash=hash_value).first()

# Good - limiting results
recent = Upload.query.order_by(Upload.upload_date.desc()).limit(10).all()

# Good - avoiding N+1
uploads = Upload.query.options(db.joinedload(Upload.summaries)).all()
```

## Common Tasks

### Update Claude Model Version

If updating the Anthropic model:

1. Change in `src/pdf_summarizer/config.py`: `DEFAULT_CLAUDE_MODEL`
2. Add to CHANGELOG.md under "Changed"
3. Update version if significant change

### Add New Configuration Option

1. Add to `src/pdf_summarizer/config.py` in `Config` class
2. Add CLI argument in `main.py` if needed
3. Add to `.env.example` if environment variable
4. Update README.md documentation
5. Add tests for the new configuration

### Add New Route/Endpoint

1. Add route in `main.py`
2. Create template in `templates/` if needed
3. Add comprehensive tests in `tests/test_routes.py`
4. Update CHANGELOG.md
5. Document in README.md if user-facing

### Fix a Bug

1. Add failing test that reproduces the bug
2. Fix the bug
3. Ensure test now passes
4. Run full test suite: `make test`
5. Update CHANGELOG.md under "Fixed"
6. Bump PATCH version

## Debugging Tips

### Database Issues

```bash
# Delete and recreate database
rm pdf_summaries.db
uv run python -m pdf_summarizer.main
```

### Test Failures

```bash
# Run single test with verbose output
uv run pytest -vv tests/test_specific.py::test_function

# Run with print statements visible
uv run pytest -s tests/test_file.py

# Run with debugger
uv run pytest --pdb tests/test_file.py
```

### Logging

Check logs in `logs/` directory:
- `app.log` - General application logs
- `error.log` - Error-level logs only
- `api.log` - External API calls to Claude

## Important Notes

1. **Never commit secrets**: Keep `.env` out of git
2. **Database migrations**: Use Flask-Migrate if schema changes
3. **API costs**: Caching reduces Claude API calls by ~60%
4. **Session management**: 30-day persistent sessions with UUID tracking
5. **Rate limiting**: 10 uploads/hour, 200 requests/day by default

## Questions or Issues?

If you encounter issues or have questions:

1. Check the [README.md](README.md) for user-facing documentation
2. Review [CHANGELOG.md](CHANGELOG.md) for recent changes
3. Check [docs/database.md](docs/database.md) for database schema and queries
4. Look at test files for usage examples
5. Check [Makefile](Makefile) for available commands

---

**Last Updated**: 2025-11-16
**Project Version**: 0.2.4
