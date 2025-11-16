# PDF Summarizer

**Version**: 0.2.5 | [Changelog](./CHANGELOG.md)

A Flask web application that uploads PDF files and generates AI-powered summaries using Anthropic's Claude API.

> **For Developers & AI Assistants**: See [CLAUDE.md](./CLAUDE.md) for development guidelines, testing instructions, code quality standards, and version management rules.

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
   cd /path/to/pdf-summarizer
   ```

2. **Set up the environment** (requires [uv](https://github.com/astral-sh/uv)):
   ```bash
   make env
   source .venv/bin/activate
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

or use my [env.sh](https://github.com/iheitlager/dotfiles/blob/main/bin/env.sh) tool to read env vars from the password manager. (Be sure `.env` is in `.gitignore`)

4. **Initialize the database**:
   The database will be automatically created when you first run the application.

## Usage

### Running the Application

1. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

2. **Run the application**:
   ```bash
   make run
   ```

3. **Open your browser**:
   Navigate to http://127.0.0.1:5000

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
├── src/pdf_summarizer/         # Main application code
│   ├── main.py                 # Flask application entry point
│   ├── config.py               # Centralized configuration
│   ├── templates/              # HTML templates
│   └── static/                 # CSS, JS, assets
├── tests/                      # Test suite (90%+ coverage)
├── docs/                       # Documentation
│   ├── database.md             # Database schema reference
│   └── adr/                    # Architecture Decision Records
├── pyproject.toml              # Dependencies and config
├── Makefile                    # Build automation
├── CLAUDE.md                   # Developer guidelines
├── CHANGELOG.md                # Version history
└── README.md                   # This file
```

## Technical Details

> **Database Schema**: See [docs/database.md](./docs/database.md) for complete database schema documentation, including tables, relationships, indexes, and query examples.

### API Configuration
- **Model**: Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`)
- **Max tokens**: 1024
- **Input limit**: ~100,000 characters per PDF

### Database
- **Engine**: SQLite (configurable via `DATABASE_URL`)
- **ORM**: Flask-SQLAlchemy
- **Tables**: `upload` (file metadata), `summary` (AI summaries)
- **Features**: Session tracking, SHA256 caching, cascade deletion

### Caching System
SHA256 hash-based deduplication for **60% potential cost reduction**:
- Automatic cache lookup before API calls
- Cache status displayed in UI
- Cross-session caching support

### Session & Rate Limiting
- **Sessions**: 30-day lifetime with UUID tracking
- **Rate limits**: 10 uploads/hour, 200 requests/day
- Custom error pages for rate limit exceeded

### Logging
Structured logging with rotating file handlers:
- `logs/app.log` - General application logs
- `logs/error.log` - Error-level logs
- `logs/api.log` - Claude API calls

### Automated Cleanup
Daily background job (default 3 AM) to delete uploads older than retention period (default 30 days)

## Security Features

- **CSRF Protection**: Flask-WTF forms with CSRF tokens
- **File Validation**:
  - Only PDF files accepted
  - 10MB file size limit
  - Secure filename sanitization
- **Input Sanitization**: werkzeug.utils.secure_filename
- **Environment Variables**: Sensitive data stored in .env

## Development

### Quick Start

```bash
make help        # Show all available commands
make test        # Run test suite with coverage
make lint        # Check code quality
make format      # Format code
```

### Testing

The project includes a comprehensive test suite with 90%+ code coverage. Run tests with:

```bash
make test
```

For detailed testing instructions, test structure, and coverage reports, see [CLAUDE.md](./CLAUDE.md#testing-guidelines).

### Code Quality

Format and lint code:

```bash
make format      # Format with black and ruff
make lint        # Check with ruff
make type-check  # Type check with mypy
```

For detailed code quality standards and development workflow, see [CLAUDE.md](./CLAUDE.md).

## Troubleshooting

**Issue**: "No module named flask"
- **Solution**: Run `make env` to set up the environment

**Issue**: "anthropic.APIError: Invalid API key"
- **Solution**: Verify your ANTHROPIC_API_KEY in the .env file

**Issue**: "File too large"
- **Solution**: Ensure PDFs are under 10MB

**Issue**: Database errors
- **Solution**: Delete `pdf_summaries.db` and restart the app to recreate it

**Issue**: Command not found errors
- **Solution**: Activate the virtual environment with `source .venv/bin/activate`

## License

This project is provided as-is for educational and development purposes.

## Credits

- Built with [Flask](https://flask.palletsprojects.com/)
- AI powered by [Anthropic Claude](https://www.anthropic.com/)
- UI built with [Bootstrap 5](https://getbootstrap.com/)
- PDF parsing with [pypdf](https://pypdf.readthedocs.io/)
