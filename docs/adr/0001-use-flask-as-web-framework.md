# ADR-0001: Use Flask as Web Framework

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: Initial project setup

## Context

The PDF Summarizer requires a web framework to handle HTTP requests, serve HTML templates, manage file uploads, and integrate with various extensions (database ORM, forms, rate limiting).

Key requirements:
- Simple file upload handling
- Template rendering for UI
- Easy integration with SQLAlchemy ORM
- CSRF protection for forms
- Session management
- Extension ecosystem for rate limiting and migrations
- Lightweight for a single-purpose application

## Decision

Use **Flask** as the web framework for the PDF Summarizer application.

Flask provides:
- Minimal boilerplate for small applications
- Strong extension ecosystem (Flask-SQLAlchemy, Flask-WTF, Flask-Limiter, Flask-Migrate)
- Built-in development server
- Jinja2 templating engine
- Simple routing and request handling
- Good documentation and community support

## Alternatives Considered

### Alternative 1: Django
- **Description**: Full-featured web framework with batteries included
- **Pros**:
  - Admin interface out of the box
  - Built-in ORM and migrations
  - More opinionated structure
  - Comprehensive security features
- **Cons**:
  - Heavyweight for a simple PDF summarization app
  - Steeper learning curve
  - More boilerplate required
  - ORM less flexible than SQLAlchemy
- **Rejected because**: Too heavyweight for our use case. We don't need admin interface, user authentication system, or the Django ORM. Flask's simplicity better matches our requirements.

### Alternative 2: FastAPI
- **Description**: Modern async web framework with automatic API documentation
- **Pros**:
  - Async/await support for better performance
  - Automatic OpenAPI documentation
  - Type hints and validation with Pydantic
  - Modern Python features
- **Cons**:
  - Designed for APIs, not traditional web apps with templates
  - Would need additional template engine setup
  - Async not needed for our use case (blocking I/O with Claude API)
  - Less mature extension ecosystem for traditional web features
- **Rejected because**: PDF Summarizer is a traditional web application with server-rendered templates, not a REST API. Flask's synchronous model is simpler and sufficient.

### Alternative 3: Bottle
- **Description**: Ultra-lightweight micro-framework
- **Pros**:
  - Single-file framework
  - Minimal dependencies
  - Very lightweight
- **Cons**:
  - Much smaller extension ecosystem
  - Less community support
  - Would need to build more from scratch
- **Rejected because**: Lack of mature extensions for SQLAlchemy integration, CSRF protection, and rate limiting would require significant custom development.

## Consequences

### Positive Consequences
- **Rapid development**: Minimal boilerplate allows quick prototyping and iteration
- **Rich extensions**: Flask-SQLAlchemy, Flask-WTF, Flask-Limiter, Flask-Migrate handle common needs
- **Template rendering**: Built-in Jinja2 integration simplifies UI development
- **Easy testing**: Flask's test client makes integration testing straightforward
- **Clear documentation**: Large community provides examples and solutions
- **Flexible architecture**: Can organize code as needed without framework constraints

### Negative Consequences
- **Manual integration**: Need to manually wire up extensions (SQLAlchemy, WTF, Limiter)
- **Less opinionated**: More decisions required about project structure
- **Synchronous only**: No built-in async support (not needed for our use case)
- **No admin UI**: Would need to build custom admin pages if needed

### Neutral Consequences
- **WSGI-based**: Standard WSGI application, works with Gunicorn, uWSGI, etc.
- **Single-threaded dev server**: Production deployment requires separate WSGI server

## Implementation Notes

### Key Flask Extensions Used
- **Flask-SQLAlchemy**: ORM integration for database models
- **Flask-Migrate**: Database migration management (Alembic wrapper)
- **Flask-WTF**: Form handling and CSRF protection
- **Flask-Limiter**: Rate limiting for abuse prevention

### Code Locations
- Application setup: [src/pdf_summarizer/main.py:68-87](../../src/pdf_summarizer/main.py#L68-L87)
- Routes: [src/pdf_summarizer/main.py:225-440](../../src/pdf_summarizer/main.py#L225-L440)
- Configuration: [src/pdf_summarizer/config.py](../../src/pdf_summarizer/config.py)

### Configuration
```python
app = Flask(__name__)
app.config.from_object(Config)

# Extensions initialization
db = SQLAlchemy(app)
migrate = Migrate(app, db)
limiter = Limiter(app=app, key_func=get_remote_address)
```

## References

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask Extensions](https://flask.palletsprojects.com/en/3.0.x/extensions/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- [Flask-WTF](https://flask-wtf.readthedocs.io/)

## Related ADRs

- Related to: ADR-0002 (SQLite with SQLAlchemy ORM)
- Related to: ADR-0010 (Flask-Limiter for Rate Limiting)
