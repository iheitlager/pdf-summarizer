# ADR-0005: Monolithic Application Architecture

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: Application architecture and deployment model

## Context

The PDF Summarizer needs an application architecture that balances simplicity, maintainability, and scalability. The primary use case is a single-purpose web application that uploads PDFs and generates summaries.

Key characteristics:
- **Single purpose**: PDF upload and summarization only
- **Low to medium scale**: Expected 10-100 users, 100-1000 requests/day
- **Simple deployment**: Should be easy to deploy and maintain
- **Minimal operational overhead**: Small team/solo developer
- **Development velocity**: Fast iteration and feature development

### Current Requirements
- Upload PDF files via web interface
- Generate AI summaries using Claude API
- Store upload history and summaries
- Session-based user tracking (no authentication)
- Rate limiting and caching
- Automated cleanup of old uploads

## Decision

Use a **monolithic application architecture** with all components in a single Flask application process.

The architecture includes:
- **Single Flask application**: All routes, logic, and background jobs in one process
- **Embedded database**: SQLite database file (pdf_summaries.db)
- **Filesystem storage**: PDF files stored in uploads/ directory
- **In-process scheduler**: APScheduler for background cleanup jobs
- **No microservices**: All features in one codebase
- **Stateful deployment**: Local disk storage (uploads/, database)

### Application Structure
```
PDF Summarizer (Monolith)
├── Web Layer (Flask routes)
├── Business Logic (summarization, caching)
├── Data Layer (SQLAlchemy models)
├── Background Jobs (APScheduler)
├── Storage (SQLite + filesystem)
└── External API (Anthropic Claude)
```

## Alternatives Considered

### Alternative 1: Microservices Architecture
- **Description**: Split into separate services (upload service, summarization service, storage service)
- **Pros**:
  - Independent scaling of components
  - Technology diversity (different languages per service)
  - Fault isolation (one service failure doesn't crash all)
  - Team autonomy (different teams per service)
  - Better for very large scale
- **Cons**:
  - Extreme operational complexity (orchestration, service discovery)
  - Network latency between services
  - Distributed transaction complexity
  - Multiple deployments required
  - Debugging across services difficult
  - Overkill for single-purpose app
  - Higher infrastructure costs
- **Rejected because**: PDF Summarizer is a simple, single-purpose application. Microservices add massive complexity without benefits at our scale. Team size (1-2 developers) cannot justify operational overhead.

### Alternative 2: Serverless Functions (AWS Lambda)
- **Description**: Deploy as serverless functions (Lambda for processing, S3 for storage, DynamoDB for data)
- **Pros**:
  - Automatic scaling to zero
  - Pay-per-request billing
  - No server management
  - Built-in fault tolerance
  - Regional redundancy
- **Cons**:
  - Cold start latency (1-5 seconds)
  - Vendor lock-in (AWS-specific)
  - Difficult local development
  - Stateless model requires external storage
  - Complex deployment pipeline
  - Hard to debug
  - 15-minute Lambda timeout may be insufficient
  - Higher cost at moderate scale
- **Rejected because**: Flask application is stateful (SQLite, filesystem). Serverless requires significant architecture changes. Cold starts hurt user experience. Development complexity not worth benefits.

### Alternative 3: Modular Monolith
- **Description**: Monolithic deployment but organized as separate internal modules with clear boundaries
- **Pros**:
  - Better code organization than pure monolith
  - Easier to extract microservices later
  - Clear separation of concerns
  - Module-level testing
  - Can enforce module boundaries
- **Cons**:
  - More upfront design required
  - Slightly more complex than simple monolith
  - Still shares database and deployment
  - Boundaries can become blurred over time
- **Rejected because**: While modular monolith is a good pattern, PDF Summarizer is small enough (~2000 LOC) that simple package organization is sufficient. Over-engineering for current scale.

### Alternative 4: Containerized Monolith (Docker + PostgreSQL)
- **Description**: Dockerize Flask app with separate PostgreSQL container
- **Pros**:
  - Better production deployment
  - Database separation
  - Easier horizontal scaling
  - CI/CD friendly
  - Reproducible environments
- **Cons**:
  - Requires Docker knowledge
  - More complex local development
  - PostgreSQL overhead for simple needs
  - Database connection pooling complexity
  - Requires container orchestration
- **Rejected because**: SQLite + filesystem sufficient for current scale. Docker adds deployment complexity. Can migrate later if scale requires. Start simple.

## Consequences

### Positive Consequences
- **Simplicity**: Single codebase, single deployment, single process to monitor
- **Fast development**: No inter-service communication, no distributed debugging
- **Easy deployment**: Copy files, run Flask app, done
- **Atomic operations**: Database transactions work correctly (no distributed transactions)
- **Low latency**: No network calls between components
- **Simple debugging**: All code in one process, standard debugging tools work
- **Cost-effective**: Single server/process runs entire application
- **Easy testing**: Test entire application without mocking services

### Negative Consequences
- **Single point of failure**: If app crashes, entire service is down
- **Vertical scaling only**: Cannot scale components independently
- **Technology lock-in**: Entire app must use Python/Flask
- **Resource sharing**: CPU-heavy summarization shares resources with web server
- **Restart required**: Code changes require full application restart
- **Shared state**: Background jobs share memory with web requests
- **Limited horizontal scaling**: Stateful design (SQLite, filesystem) hard to scale

### Neutral Consequences
- **Good fit for scale**: 10-100 users fit easily in monolith
- **Can migrate later**: Can extract services if scale requires (not likely)
- **Deployment simplicity**: Trade-off of scaling flexibility for operational simplicity

## Implementation Notes

### Project Structure
```
src/pdf_summarizer/
├── __init__.py           # Package initialization
├── main.py               # Flask app, routes, ALL logic
├── models.py             # Database models
├── config.py             # Configuration
├── logging_config.py     # Logging setup
├── utils.py              # Helper functions
├── templates/            # Jinja2 templates
└── static/               # CSS, JS, images
```

### Single Process Components
```python
# main.py - Everything in one file
app = Flask(__name__)                    # Web server
db = SQLAlchemy(app)                     # Database ORM
limiter = Limiter(app=app)               # Rate limiting
scheduler = BackgroundScheduler()        # Background jobs
client = Anthropic(api_key=...)          # External API client

@app.route('/upload')                    # Web routes
def upload(): ...

def summarize_pdf(text):                 # Business logic
    return client.messages.create(...)

def cleanup_old_uploads():               # Background job
    Upload.query.filter(...).delete()

scheduler.add_job(cleanup_old_uploads)   # Schedule cleanup
```

### Deployment Model
```bash
# Single command to run entire app
uv run python -m pdf_summarizer.main

# Or with production server
gunicorn pdf_summarizer.main:app
```

### Code Locations
- Main application: [src/pdf_summarizer/main.py](../../src/pdf_summarizer/main.py)
- Configuration: [src/pdf_summarizer/config.py](../../src/pdf_summarizer/config.py)
- Models: [src/pdf_summarizer/models.py](../../src/pdf_summarizer/models.py)

## Scalability Considerations

### When to Migrate from Monolith
Consider breaking up the monolith if:
- **Users > 1000 concurrent**: Web server becomes bottleneck
- **Requests > 10K/day**: Database/filesystem performance degrades
- **Team size > 5 developers**: Code conflicts and coordination overhead increase
- **Multi-tenancy required**: Different customers need isolation
- **Geographic distribution needed**: Users in multiple regions require local deployments

### Current Scale Adequacy
- SQLite handles: 100K requests/day easily
- Flask dev server: 10-50 concurrent users
- Filesystem storage: Millions of files possible
- APScheduler: Dozens of background jobs
- **Conclusion**: Monolith sufficient for 5-10x current expected scale

### Migration Path (if needed)
1. **Extract background jobs**: Move APScheduler to separate worker process
2. **Add PostgreSQL**: Replace SQLite when concurrent writes become issue
3. **Extract summarization**: Move Claude API calls to worker queue
4. **Add caching layer**: Redis for session/cache if needed
5. **Horizontal scaling**: Load balancer + multiple Flask instances

## Performance Characteristics

### Current Performance
- **Request latency**: 50-200ms (without Claude API)
- **Summarization**: 2-10 seconds (Claude API latency)
- **Database queries**: <1ms (SQLite indexed queries)
- **File uploads**: 100-500ms (10MB PDF)
- **Memory usage**: ~100-200MB (single process)
- **CPU usage**: Low except during summarization

### Bottlenecks
- **Claude API latency**: Main user-facing delay (cannot optimize)
- **Blocking I/O**: Summarization blocks request thread (acceptable for scale)
- **Single-threaded dev server**: Use Gunicorn in production for concurrency

## References

- [Monolith vs Microservices](https://martinfowler.com/articles/microservices.html)
- [Majestic Monolith](https://m.signalvnoise.com/the-majestic-monolith/)
- [When to use microservices](https://martinfowler.com/articles/microservice-trade-offs.html)
- [Flask Application Structure](https://flask.palletsprojects.com/en/3.0.x/patterns/)

## Related ADRs

- Related to: ADR-0001 (Use Flask as Web Framework)
- Related to: ADR-0002 (Use SQLite with SQLAlchemy ORM)
- Related to: ADR-0008 (Store PDF Files on Filesystem)
- Related to: ADR-0009 (Use APScheduler for Background Jobs)
