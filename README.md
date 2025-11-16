# PDF Summarizer

**Version**: 0.2.3 | [Changelog](./CHANGELOG.md)

A Flask web application that uploads PDF files and generates AI-powered summaries using Anthropic's Claude API.

Inspiration from [here](https://medium.com/coding-nexus/the-best-ai-coding-setup-ive-ever-used-54482f9bf080).



## Features

- **Multi-file PDF Upload**: Upload multiple PDF files simultaneously (max 10MB each)
- **AI-Powered Summaries**: Generate concise summaries using Claude 3.5 Sonnet
- **Persistent Storage**: Store PDFs and summaries in a SQLite database
- **Download Summaries**: Download summaries as text files
- **Modern UI**: Responsive Bootstrap 5 interface with drag-and-drop support
- **Security**: CSRF protection, secure filename handling, file type validation
- **Summary Caching**: SHA256 hash-based deduplication to prevent re-processing identical PDFs
- **Session Management**: Persistent user sessions with 30-day lifetime and personalized upload history
- **Rate Limiting**: Abuse prevention with configurable request limits (10 uploads/hour, 200 requests/day)
- **Comprehensive Logging**: Structured logging system with rotating file handlers for app, error, and API logs
- **Automated Cleanup**: Daily background job to automatically delete uploads older than retention period (default: 30 days)
- **Error Handling**: Custom error pages with user-friendly messages for 404, 429, and 500 errors

## Prerequisites

- Python 3.13 or higher
- Anthropic API key ([Get one here](https://console.anthropic.com/))

## Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd /Users/iheitlager/wc/new
   ```

2. **Set up complete development environment**:
   ```bash
   make env
   source .venv/bin/activate
   ```

   Or individually:
   ```bash
   make install           # Install application packages
   make install-dev       # Install development packages
   source .venv/bin/activate
   ```

   Or manually with uv:
   ```bash
   uv venv .venv
   . .venv/bin/activate
   uv pip install -e .              # Install app packages
   uv pip install -e ".[dev]"       # Install dev packages
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   SECRET_KEY=your-secret-key-here
   LOG_LEVEL=INFO
   RETENTION_DAYS=30
   CLEANUP_HOUR=3
   ```

4. **Initialize the database**:
   The database will be automatically created when you first run the application.
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   SECRET_KEY=your-secret-key-here
   LOG_LEVEL=INFO
   RETENTION_DAYS=30
   CLEANUP_HOUR=3
   ```

4. **Initialize the database**:
   The database will be automatically created when you first run the application.

## Usage

### Running the Application

1. **Set up the environment** (first time only):
   ```bash
   make env
   ```

2. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

3. **Run the application**:
   ```bash
   make run
   ```
   
   Or manually:
   ```bash
   python -m pdf_summarizer.main
   ```

4. **Open your browser**:
   Navigate to `http://127.0.0.1:5000`

### Using the Application

1. **Upload PDFs**:
   - Click to select PDF files or drag and drop them
   - Multiple files can be uploaded at once
   - Each file must be a PDF and under 10MB

2. **View summaries**:
   - Summaries are displayed on the results page
   - Click "Download" to save a summary as a text file
   - View all past summaries from the "All Summaries" link

## Project Structure
```
.
├── src/                            # Main application package
│   └── pdf_summarizer/             # Application code
│       ├── __init__.py             # Package initialization
│       ├── main.py                 # Flask application entry point
│       ├── logging_config.py       # Structured logging configuration
│       ├── templates/              # HTML Jinja2 templates
│       │   ├── base.html           # Base template with common layout
│       │   ├── index.html          # PDF upload page
│       │   ├── results.html        # Summary results page
│       │   └── errors/             # Error page templates
│       │       ├── 404.html        # Page Not Found
│       │       ├── 429.html        # Rate Limit Exceeded
│       │       └── 500.html        # Internal Server Error
│       ├── static/                 # Static assets
│       │   ├── css/
│       │   │   └── style.css       # Custom styles
│       │   └── js/
│       │       └── main.js         # Client-side JavaScript
│       ├── uploads/                # PDF file storage directory
├── tests/                          # Unit and integration tests
│   ├── __init__.py                 # Test package initialization
│   ├── test_*.py                   # Test modules
├── pyproject.toml                  # Project dependencies and configuration
├── Makefile                        # Build automation (make env, make test, make clean)
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── README.md                       # Project documentation
├── CHANGELOG.md                    # Version history and feature changelog
```
```

## Database Schema

### Upload Table
- `id`: Primary key
- `filename`: Secure filename on disk
- `original_filename`: Original uploaded filename
- `file_path`: Full path to stored file
- `upload_date`: Timestamp of upload
- `file_size`: Size in bytes

### Summary Table
- `id`: Primary key
- `upload_id`: Foreign key to Upload
- `summary_text`: Generated summary
- `created_date`: Timestamp of summary creation
- `page_count`: Number of pages in PDF
- `char_count`: Character count of extracted text

## API Usage

The application uses the Anthropic Claude API with the following configuration:
- Model: `claude-3-5-sonnet-20241022`
- Max tokens: 1024
- Input limit: ~100,000 characters per PDF

## Caching System

The application prevents re-processing of identical PDFs using SHA256 hash-based deduplication:
- Automatic cache lookup before Claude API calls
- **60% potential cost reduction** for duplicate PDFs
- Cache status displayed in UI with badge indicators
- Cache hits logged for monitoring

## Session Management

Personalized experience with persistent user sessions:
- 30-day session lifetime with UUID-based tracking
- "My Uploads" page at `/my-uploads` shows user's own uploads
- Homepage displays only current session's recent uploads
- Automatic session creation and logging

## Rate Limiting

Abuse prevention through Flask-Limiter:
- 10 PDF uploads per hour limit
- 200 total requests per day limit
- Custom 429 (Rate Limit Exceeded) error page
- Configurable storage backend (memory/Redis)

## Logging System

Structured logging with rotating file handlers:
- `logs/app.log` - General application logs (INFO and above)
- `logs/error.log` - Error-level logs only
- `logs/api.log` - External API calls to Claude
- Configurable via `LOG_LEVEL` environment variable (default: INFO)

## Automated Cleanup

Daily background job to maintain database:
- Default cleanup time: 3 AM (configurable via `CLEANUP_HOUR`)
- Automatic deletion of uploads older than retention period (default: 30 days via `RETENTION_DAYS`)
- File system and database cleanup with metrics logging
- Graceful scheduler shutdown handling

## Security Features

- **CSRF Protection**: Flask-WTF forms with CSRF tokens
- **File Validation**:
  - Only PDF files accepted
  - 10MB file size limit
  - Secure filename sanitization
- **Input Sanitization**: werkzeug.utils.secure_filename
- **Environment Variables**: Sensitive data stored in .env

## Development

To run in development mode with debug enabled:

```bash
export FLASK_ENV=development
python main.py
```

### Testing

The project includes a comprehensive test suite with 90%+ code coverage targeting all application components.

#### Running Tests

Run the complete test suite with coverage:

```bash
make test
```

Or manually:
```bash
pytest
```

#### Coverage Reports

View coverage in the terminal:
```bash
pytest --cov=. --cov-report=term-missing
```

Generate and view HTML coverage report:
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

#### Test Structure

The test suite includes 13 comprehensive test modules:

- **`tests/conftest.py`** - Core fixtures and test configuration (20+ fixtures)
  - Mock Anthropic API responses
  - PDF generators (sample, multi-page, empty, corrupted, large)
  - Database fixtures with auto-reset
  - Temporary directories and mock loggers

- **Unit Tests**:
  - `test_helpers.py` - All helper functions (hashing, caching, extraction, summarization, file handling, cleanup, sessions)
  - `test_models.py` - Database models (creation, relationships, queries, cascade deletion)
  - `test_forms.py` - Form validation (CSRF, file type/size limits)

- **Integration Tests**:
  - `test_routes.py` - All endpoints (upload, results, download, my-uploads, all-summaries)
  - `test_error_handlers.py` - Error pages (404, 500, 429)

- **Feature Tests**:
  - `test_caching.py` - Cache hits/misses, cross-session caching, API call avoidance
  - `test_session.py` - Session isolation, persistence, multi-user scenarios
  - `test_cleanup.py` - Date-based deletion, metrics logging, error handling
  - `test_logging.py` - Log creation, formatting, API logging

- **End-to-End Tests**:
  - `test_integration.py` - Complete workflows (upload→process→view→download)

#### Running Specific Tests

Run a specific test file:
```bash
pytest tests/test_helpers.py
```

Run a specific test class:
```bash
pytest tests/test_routes.py::TestIndexRoute
```

Run a specific test function:
```bash
pytest tests/test_caching.py::TestCachingMechanism::test_cache_hit_avoids_api_call
```

Run with verbose output:
```bash
pytest -v
```

#### Test Features

- **Isolated Testing**: Each test runs with a fresh SQLite in-memory database
- **Mock API Calls**: Anthropic API calls are mocked to avoid external dependencies
- **Dynamic PDF Generation**: Tests generate PDFs on-the-fly using reportlab
- **Comprehensive Coverage**: Tests cover success paths, error cases, and edge cases
- **Fast Execution**: In-memory database and mocked APIs ensure quick test runs

### Code Quality Tools

Format and lint code with Ruff and Black:

```bash
# Format code
black .

# Lint code
ruff check .

# Fix linting issues automatically
ruff check --fix .

# Type check with MyPy
mypy .
```

## Database Migrations (Optional)

If you need to modify the database schema:

```bash
# Initialize migrations
flask db init

# Create a migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade
```

## Troubleshooting

**Issue**: "No module named flask"
- **Solution**: Install dependencies with `pip install -e .`

**Issue**: "anthropic.APIError: Invalid API key"
- **Solution**: Verify your ANTHROPIC_API_KEY in the .env file

**Issue**: "File too large"
- **Solution**: Ensure PDFs are under 10MB

**Issue**: Database errors
- **Solution**: Delete `pdf_summaries.db` and restart the app to recreate it

## License

This project is provided as-is for educational and development purposes.

## Credits

- Built with [Flask](https://flask.palletsprojects.com/)
- AI powered by [Anthropic Claude](https://www.anthropic.com/)
- UI built with [Bootstrap 5](https://getbootstrap.com/)
- PDF parsing with [pypdf](https://pypdf.readthedocs.io/)
