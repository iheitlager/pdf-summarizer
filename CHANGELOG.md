# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
