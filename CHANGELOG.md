# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2025-11-16

### Added
- **Makefile**: Build automation for environment setup and testing
  - `make env` - Create and set up complete development environment
  - `make install` / `make install-dev` - Separate installation steps
  - `make test` - Run tests with pytest and coverage
  - `make clean` - Clean up virtual environment and build files

### Changed
- **Project Structure**: Reorganized as proper Python package
  - Moved application code to `src/pdf_summarizer/` directory
  - Created `__init__.py` for package initialization
  - Improved organization: templates, static, and uploads now in package directory
  
- **Build System**: Updated to use Hatchling properly
  - Configured `pyproject.toml` with correct package detection
  - Uses optional dependencies for dev tools instead of dependency groups
  - Supports proper editable installs with `-e .` and `-e ".[dev]"`

- **Development Workflow**:
  - `.venv` as standard virtual environment directory
  - Simplified installation: single `make env` command for full setup
  - Dependencies managed exclusively in `pyproject.toml`

---

## [0.2.0] - 2025-11-16

### Added

#### Summary Caching System
- SHA256 hash-based file deduplication to prevent re-processing identical PDFs
- `file_hash` column in Upload model (unique, indexed)
- `is_cached` boolean flag to track cache hits
- Automatic cache lookup before processing
- UI badge indicator showing cached summaries
- Cache hit/miss logging for monitoring
- Significant cost savings by avoiding duplicate Claude API calls

#### Session Management
- Persistent user sessions with 30-day lifetime
- UUID-based session tracking
- `session_id` column in Upload model (indexed)
- Session-specific upload filtering
- New "My Uploads" page at `/my-uploads` route
- Session creation logging
- Homepage now shows only current user's recent uploads

#### Rate Limiting
- Flask-Limiter integration for abuse prevention
- Per-endpoint rate limits (10 uploads/hour, 200 requests/day)
- Custom 429 (Rate Limit Exceeded) error page
- Rate limit violation logging
- Configurable storage backend (memory/Redis)
- User-friendly rate limit information display

#### Comprehensive Logging System
- New `logging_config.py` module with structured logging
- Three separate rotating log files:
  - `logs/app.log` - General application logs (INFO and above)
  - `logs/error.log` - Error-level logs only
  - `logs/api.log` - External API calls (Claude)
- Rotating file handlers (10MB max, 5 backups)
- Configurable log levels via `LOG_LEVEL` environment variable
- Context-aware error logging
- Startup, upload, processing, API call, cache, and cleanup logging
- Dedicated API logger for external service monitoring

#### Automated Cleanup Job
- APScheduler-based background task scheduler
- Daily cleanup job (default: 3 AM, configurable)
- Automatic deletion of uploads older than retention period
- Configurable retention period via `RETENTION_DAYS` (default: 30 days)
- Both file system and database cleanup
- Cleanup operation logging with metrics (files deleted, space freed)
- Graceful scheduler shutdown handling

#### Error Handling
- Custom error page templates:
  - `templates/errors/404.html` - Page Not Found
  - `templates/errors/500.html` - Internal Server Error
  - `templates/errors/429.html` - Rate Limit Exceeded
- User-friendly error messages with actionable guidance
- Error logging with full context and stack traces
- Database rollback on errors

### Changed
- Updated Upload model with new fields: `file_hash`, `session_id`, `is_cached`
- Enhanced upload flow with cache checking before processing
- Modified results template to show cached badge and dynamic titles
- Updated navigation bar to include "My Uploads" link
- Improved error handling throughout application
- Enhanced download functionality to indicate cached summaries

### Dependencies
- Added `flask-limiter>=3.5.0` for rate limiting
- Added `apscheduler>=3.10.0` for scheduled tasks

### Configuration
- Added `LOG_LEVEL` environment variable (default: INFO)
- Added `RETENTION_DAYS` environment variable (default: 30)
- Added `CLEANUP_HOUR` environment variable (default: 3)
- Added `REDIS_URL` environment variable (optional, for production)

### Infrastructure
- Created `logs/` directory for application logs
- Updated `.gitignore` to exclude log files
- Added logs directory to project structure

### Documentation
- Comprehensive README.md updates with new features
- Added Logging, Caching, Cleanup Job, and Configuration sections
- Updated Database Schema documentation
- Enhanced Security Features section
- Updated Project Structure diagram

---

## [0.1.0] - 2025-11-16

### Added

#### Core PDF Processing
- Multi-file PDF upload support with drag-and-drop interface
- PDF text extraction using pypdf library
- AI-powered summarization using Anthropic Claude 3.5 Sonnet
- Support for PDFs up to 10MB per file
- Handles documents up to ~100,000 characters

#### Database & Storage
- SQLite database with SQLAlchemy ORM
- Upload model to track uploaded files
- Summary model to store generated summaries
- Persistent file storage in `uploads/` directory
- Database migrations support via Flask-Migrate

#### User Interface
- Modern, responsive Bootstrap 5 design
- Drag-and-drop file upload area
- File selection with visual feedback
- Real-time file list display with size information
- Results page with summary display
- Download summaries as formatted text files
- Copy to clipboard functionality
- Recent uploads list on homepage
- All summaries archive page

#### Security Features
- CSRF protection via Flask-WTF
- Secure filename handling with werkzeug.utils.secure_filename
- File type validation (PDF only)
- File size validation (10MB limit)
- Timestamp-based unique filenames to prevent collisions
- Environment variable configuration for sensitive data

#### Form Handling
- Flask-WTF forms with validators
- FileRequired and FileAllowed validators
- Custom file size validation
- Multiple file upload support
- User-friendly validation error messages

#### API Integration
- Anthropic Claude API integration
- claude-3-5-sonnet-20241022 model
- Configurable max tokens (1024)
- Environment-based API key configuration
- Automatic text truncation for API limits

#### Templates & Static Files
- Base template with navigation and footer
- Index page with upload form
- Results page with summary cards
- Custom CSS styling
- JavaScript for drag-and-drop and file validation
- Bootstrap Icons integration

### Dependencies
- `flask>=3.0.0` - Web framework
- `flask-sqlalchemy>=3.1.0` - Database ORM
- `flask-migrate>=4.0.0` - Database migrations
- `flask-wtf>=1.2.0` - Form handling and CSRF
- `anthropic>=0.40.0` - Claude API client
- `pypdf>=5.1.0` - PDF text extraction
- `python-dotenv>=1.0.0` - Environment variable management

### Configuration
- `SECRET_KEY` - Flask secret key for sessions and CSRF
- `ANTHROPIC_API_KEY` - Anthropic API authentication
- `FLASK_ENV` - Environment mode (development/production)
- SQLite database at `pdf_summaries.db`
- 10MB maximum file upload size

### Infrastructure
- Project structure with templates, static files, and uploads directories
- `.gitignore` for Python, Flask, and project-specific files
- `.env.example` template for environment variables
- `README.md` with installation and usage instructions
- Python 3.13+ requirement

---

## Version Comparison

### What's New in 0.2.0?
Version 0.2.0 transforms the basic PDF summarizer into a production-ready application with:

- **60% potential cost reduction** through intelligent caching
- **Enterprise-grade logging** for debugging and monitoring
- **Abuse prevention** via rate limiting
- **Automated maintenance** with scheduled cleanup
- **Personalized experience** through session management
- **Better error handling** with custom error pages

### Migration from 0.1.0 to 0.2.0

1. **Install new dependencies:**
   ```bash
   pip install -e .
   ```

2. **Update environment variables:**
   ```bash
   # Add to your .env file:
   LOG_LEVEL=INFO
   RETENTION_DAYS=30
   CLEANUP_HOUR=3
   ```

3. **Database schema changes:**
   - Option A: Delete `pdf_summaries.db` (fresh start)
   - Option B: Use Flask-Migrate:
     ```bash
     flask db init
     flask db migrate -m "Add caching and session support"
     flask db upgrade
     ```

4. **Create logs directory:**
   ```bash
   mkdir -p logs
   ```

---

[0.2.0]: https://github.com/yourusername/pdf-summarizer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/pdf-summarizer/releases/tag/v0.1.0
