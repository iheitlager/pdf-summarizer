# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-11-17

### Added
- **Prompt Template Management**: CRUD interface for managing reusable prompt templates
- **Prompt Selection on Upload**: Dropdown to select prompt template when uploading PDFs
- **PromptTemplate Model**: New database table for storing prompt templates with name, text, and active status
- **Default Prompt Seeding**: Automatic creation of "Basic Summary" prompt on first run
- **Prompt-Aware Caching**: Cache key now includes both file hash and prompt template ID

### Changed
- **Summary Model**: Added `prompt_template_id` foreign key to track which prompt was used
- **Cache Behavior**: Different prompts on same PDF now create separate summaries (cache miss)
- **Upload Form**: Added prompt template selection dropdown with default selection

---

## [0.2.6] - 2025-11-17

### Added
- **Application Factory Pattern**: New `factory.py` module with `create_app()` function for proper Flask app initialization
- **Flask Extensions Module**: New `extensions.py` with singleton extension instances (`db`, `limiter`, `migrate`, `anthropic_ext`, `cleanup_scheduler`)
- **Modular Route Handlers**: New `routes.py` module containing all route handlers and helper functions
- **Error Handlers Module**: New `error_handlers.py` for centralized error handling (404, 429, 500)
- **Forms Module**: New `forms.py` containing Flask-WTF form definitions
- **Claude Service Module**: New `claude_service.py` for AI summarization functionality
- **Cleanup Service Module**: New `cleanup.py` for background cleanup job logic

### Changed
- **Major Refactoring**: Restructured entire application following Flask best practices and application factory pattern
- **Separation of Concerns**: Extracted functionality from monolithic `main.py` into 7 specialized modules
- **Extension Initialization**: Extensions now properly initialized via factory pattern, preventing duplicate scheduler/client instances
- **Test Infrastructure**: Updated all tests to use factory pattern with proper dependency injection
- **Main Module**: Reduced `main.py` to slim entry point with backward compatibility layer for existing tests

### Technical Improvements
- Scheduler properly managed via extension wrapper, only starts when explicitly enabled (prevents duplicate jobs in tests)
- Anthropic client managed as Flask extension with proper lifecycle
- Database models properly imported before `db.create_all()` for correct SQLAlchemy registration
- Rate limiter configuration streamlined via extension pattern
- All tests updated to import from new modular structure

---

## [0.2.5] - 2025-11-16

### Changed
- **Database Models Refactoring**: Moved database models (`Upload`, `Summary`, `db`) from `main.py` to dedicated `models.py` module
- Updated documentation to reflect new model location in `docs/database.md` and `CLAUDE.md`
- Improved code organization and separation of concerns

---

## [0.2.4] - 2025-11-16

### Added
- **Centralized Configuration**: New `config.py` module with all application settings
- **Command-Line Arguments**: CLI support via argparse for `--host`, `--port`, `--debug`, `--api-key`, `--database`, `--upload-folder`, `--log-level`, and `--retention-days`
- **Configuration Validation**: Automatic startup validation with clear error messages

### Changed
- **Configuration Management**: All settings centralized in `Config` class
- **Default Claude Model**: Updated to `claude-sonnet-4-5-20250929`
- Refactored `main.py` and `logging_config.py` to use centralized configuration
- Configuration now supports environment variables and CLI argument overrides
- Improved error handling for missing required configuration

---

## [0.2.3] - 2025-11-16

### Added
- **Apache 2.0 License**: Full LICENSE file with Apache License 2.0 text
- **Copyright Headers**: Added copyright and SPDX license identifiers to all Python source files

### Changed
- **Dynamic Versioning**: Version now read from `src/pdf_summarizer/__init__.py` using Hatchling's dynamic version support

---

## [0.2.2] - 2025-11-16

### Added
- **Comprehensive test suite** with 90%+ code coverage
  - 13 test modules covering all components
  - 20+ pytest fixtures for mocking, databases, PDFs, and logging
  - Mock Anthropic API and dynamic PDF generation
  - Unit, integration, and end-to-end tests
- **Test dependencies**: pytest, pytest-flask, pytest-cov, pytest-mock, reportlab
- **Documentation**: Test execution and coverage reporting in README

---

## [0.2.1] - 2025-11-16

### Added
- **Makefile** with automation targets: `make env`, `make test`, `make clean`, etc.

### Changed
- **Project structure**: Reorganized as proper Python package under `src/pdf_summarizer/`
- **Build system**: Updated to use Hatchling with `pyproject.toml`
- **Development workflow**: Simplified with single `make env` command for full setup

---

## [0.2.0] - 2025-11-16

### Added
- **Summary Caching**: SHA256 hash-based deduplication (60% potential cost reduction)
- **Session Management**: Persistent 30-day sessions with UUID tracking and "My Uploads" page
- **Rate Limiting**: Flask-Limiter with configurable limits (10 uploads/hour, 200 requests/day)
- **Comprehensive Logging**: Rotating file handlers for app, error, and API logs
- **Automated Cleanup**: APScheduler background job for daily upload pruning
- **Error Handling**: Custom 404, 500, and 429 error pages
- **Dependencies**: Added flask-limiter, apscheduler
- **Configuration**: LOG_LEVEL, RETENTION_DAYS, CLEANUP_HOUR environment variables

### Changed
- **Upload model**: Added `file_hash`, `session_id`, `is_cached` fields
- **Upload flow**: Cache checking before processing
- **Navigation**: Added "My Uploads" and "All Summaries" links

---

## [0.1.0] - 2025-11-16

### Added
- **Core Features**: Multi-file PDF upload, text extraction, AI summarization
- **Database**: SQLAlchemy ORM with Upload/Summary models, SQLite backend
- **UI**: Responsive Bootstrap 5 design with drag-and-drop upload
- **Security**: CSRF protection, secure filename handling, file validation
- **Forms**: Flask-WTF with custom validation
- **API**: Anthropic Claude integration (claude-3-5-sonnet-20241022)
- **Dependencies**: flask, flask-sqlalchemy, flask-migrate, flask-wtf, anthropic, pypdf, python-dotenv
- **Configuration**: Environment variables for SECRET_KEY, ANTHROPIC_API_KEY, FLASK_ENV

---

[0.2.0]: https://github.com/yourusername/pdf-summarizer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/pdf-summarizer/releases/tag/v0.1.0
