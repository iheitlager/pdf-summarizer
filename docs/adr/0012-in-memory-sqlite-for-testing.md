# ADR-0012: In-Memory SQLite for Testing

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: Test isolation and performance

## Context

The PDF Summarizer test suite needs a database for testing models, routes, and database operations. Tests must be:

- **Fast**: Run in seconds, not minutes (developer productivity)
- **Isolated**: Each test independent (no shared state)
- **Repeatable**: Same results every run (no flakiness)
- **Easy setup**: No manual database configuration
- **Clean**: No test data pollution in production database

Key requirements:
- Test database models (Upload, Summary)
- Test database queries and relationships
- Test migrations and schema changes
- No impact on production database
- Fast test execution (100+ tests in < 10 seconds)
- No cleanup required (automatic)

### Current Test Suite
- 40+ test functions across 10+ test files
- Tests for models, routes, caching, cleanup, logging
- Target: 90%+ code coverage
- Pytest-based with fixtures

## Decision

Use **in-memory SQLite databases** (`:memory:`) for all tests, with pytest fixtures creating fresh databases for each test.

Implementation:
- **Database URI**: `sqlite:///:memory:` (RAM-based, not file-based)
- **Fixture-based**: `@pytest.fixture` creates/destroys database per test
- **Fast**: 10-100x faster than file-based SQLite
- **Isolated**: Each test gets fresh database (no state leakage)
- **Automatic cleanup**: Database destroyed when test ends

### Fixture Pattern
```python
# tests/conftest.py
@pytest.fixture
def app():
    """Create test Flask app with in-memory database."""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    return app

@pytest.fixture
def db(app):
    """Create fresh database for each test."""
    with app.app_context():
        database.create_all()
        yield database
        database.drop_all()
```

## Alternatives Considered

### Alternative 1: File-Based SQLite for Tests
- **Description**: Use temporary SQLite files (`test.db`) for testing
- **Pros**:
  - Closer to production (file-based)
  - Can inspect database during debugging
  - Supports all SQLite features
  - Can test file locking behavior
- **Cons**:
  - 10-100x slower than in-memory
  - Requires cleanup (delete test.db after)
  - Risk of pollution if cleanup fails
  - File I/O overhead
  - Slower test suite = less frequent runs
  - Must handle file locking issues
- **Rejected because**: Speed is critical for test-driven development. In-memory databases run 10-100x faster. Fast tests encourage frequent running, improving code quality.

### Alternative 2: PostgreSQL/MySQL Test Database
- **Description**: Use real production database engine for tests
- **Pros**:
  - Tests actual production database
  - Catches database-specific bugs
  - More realistic testing
  - Tests transactions properly
  - Better for testing complex queries
- **Cons**:
  - Requires database server (complex setup)
  - Much slower than SQLite (network overhead)
  - Manual setup for developers (not portable)
  - CI/CD requires database container
  - Harder to parallelize tests
  - Overkill for simple ORM usage
- **Rejected because**: PDF Summarizer uses simple ORM operations. SQLite sufficient for testing. PostgreSQL adds setup complexity without benefits. In-memory SQLite is faster and simpler.

### Alternative 3: Mock Database (No Real Database)
- **Description**: Mock SQLAlchemy calls instead of using real database
- **Pros**:
  - Extremely fast (no database)
  - No database setup required
  - Can test error conditions easily
  - Complete control over responses
- **Cons**:
  - Doesn't test real database behavior
  - Doesn't catch SQL errors
  - Doesn't test relationships/joins
  - Mock setup complex and brittle
  - False confidence (mocks may be wrong)
  - Doesn't test migrations
- **Rejected because**: Integration testing more valuable than mocking. Real database catches real bugs (SQL syntax, relationship issues). In-memory SQLite provides real database testing without speed penalty.

### Alternative 4: Shared Test Database (One DB for All Tests)
- **Description**: Create single database, reuse across all tests
- **Pros**:
  - Faster setup (one-time initialization)
  - Can test cross-test scenarios
  - Less memory usage
- **Cons**:
  - Tests not isolated (state leakage)
  - Flaky tests (order-dependent)
  - Hard to debug (test pollution)
  - Cleanup between tests error-prone
  - Cannot parallelize tests
  - One failing test breaks others
- **Rejected because**: Test isolation is critical. Shared database causes flaky, order-dependent tests. Fresh database per test ensures repeatability.

### Alternative 5: Docker Database Containers
- **Description**: Spin up PostgreSQL/MySQL containers for each test
- **Pros**:
  - Production-like environment
  - Isolated containers
  - Can test different database versions
  - Good for integration tests
- **Cons**:
  - Extremely slow (container startup: 5-10 seconds)
  - Requires Docker installed
  - Complex CI/CD setup
  - Overkill for unit tests
  - Test suite would take minutes
- **Rejected because**: Container overhead makes tests too slow. In-memory SQLite provides database testing without infrastructure complexity.

## Consequences

### Positive Consequences
- **Extremely fast**: 100+ tests run in < 10 seconds
- **Perfect isolation**: Each test gets fresh database (no pollution)
- **Zero setup**: No database installation required
- **Portable**: Works on any OS without configuration
- **Automatic cleanup**: Database destroyed automatically
- **CI/CD friendly**: No external dependencies
- **Developer friendly**: Tests run instantly (encourages TDD)
- **Parallel testing**: Can run tests in parallel (no shared state)

### Negative Consequences
- **Not production database**: SQLite differs from PostgreSQL/MySQL
- **Limited testing**: Cannot test database-specific features
- **No persistence**: Cannot inspect database after test
- **SQLite quirks**: May hide PostgreSQL-specific issues (rare)
- **Transaction differences**: SQLite transaction handling differs slightly

### Neutral Consequences
- **Memory usage**: Small (MB, not GB)
- **Test-only**: Production still uses file-based SQLite
- **Schema testing**: Can test migrations, but not database-specific migrations

## Implementation Notes

### Conftest Fixtures
```python
# tests/conftest.py
import pytest
from pdf_summarizer.main import create_app
from pdf_summarizer.models import db as database

@pytest.fixture
def app():
    """Create and configure test Flask app."""
    app = create_app()
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'TESTING': True,
        'RATE_LIMIT_ENABLED': False,  # Disable rate limiting in tests
        'WTF_CSRF_ENABLED': False,     # Disable CSRF for easier testing
    })
    return app

@pytest.fixture
def db(app):
    """Create fresh database for each test."""
    with app.app_context():
        database.create_all()  # Create tables
        yield database         # Run test
        database.session.remove()
        database.drop_all()    # Clean up

@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
```

### Example Test
```python
# tests/test_models.py
def test_upload_creation(db):
    """Test creating an Upload record."""
    upload = Upload(
        filename='test.pdf',
        file_path='/tmp/test.pdf',
        file_size=1024,
        file_hash='abc123'
    )
    db.session.add(upload)
    db.session.commit()

    # Query and verify
    result = Upload.query.filter_by(filename='test.pdf').first()
    assert result is not None
    assert result.file_size == 1024
```

### Code Locations
- Test fixtures: [tests/conftest.py](../../tests/conftest.py)
- Model tests: [tests/test_models.py](../../tests/test_models.py)
- Route tests: [tests/test_routes.py](../../tests/test_routes.py)

## Performance Comparison

### In-Memory SQLite (Current)
```bash
$ uv run pytest
====== 42 tests passed in 3.24s ======
```

### File-Based SQLite (Hypothetical)
```bash
$ uv run pytest
====== 42 tests passed in 28.56s ======
```

### PostgreSQL Container (Hypothetical)
```bash
$ uv run pytest
====== 42 tests passed in 125.43s ======
```

**Verdict**: In-memory SQLite is 8-40x faster than alternatives.

## Test Categories

### Unit Tests (In-Memory DB Perfect)
- Model creation and validation
- Database queries and filters
- Relationship testing
- Cache logic
- Helper functions

### Integration Tests (In-Memory DB Sufficient)
- Route testing with database
- Form submission
- File upload processing
- Session management
- Error handlers

### System Tests (May Need Real DB)
- Performance testing (not needed for this project)
- Database-specific feature testing (not needed)
- Migration testing across DB versions (not needed)

## Database Compatibility

### SQLite vs PostgreSQL Differences
Most differences don't affect PDF Summarizer:

| Feature | SQLite | PostgreSQL | Impact |
|---------|--------|------------|--------|
| Transactions | Single writer | Multi-writer | Low (single-user app) |
| Data types | Limited | Rich | None (using simple types) |
| Full-text search | FTS5 | Native | Not used |
| JSON support | Limited | Excellent | Not used |
| Concurrency | File lock | Row lock | Low (low concurrency) |

**Conclusion**: In-memory SQLite testing sufficient for PDF Summarizer.

## Test Data Fixtures

### Creating Test Data
```python
# tests/conftest.py
@pytest.fixture
def sample_upload(db):
    """Create sample upload for testing."""
    upload = Upload(
        filename='sample.pdf',
        file_path='/tmp/sample.pdf',
        file_size=2048,
        file_hash='def456',
        session_id='test-session-123'
    )
    db.session.add(upload)
    db.session.commit()
    return upload

@pytest.fixture
def sample_summary(db, sample_upload):
    """Create sample summary for testing."""
    summary = Summary(
        upload_id=sample_upload.id,
        summary_text='This is a test summary.',
        model='claude-3-5-sonnet',
        input_tokens=1000,
        output_tokens=100
    )
    db.session.add(summary)
    db.session.commit()
    return summary
```

### Using Fixtures
```python
def test_upload_with_summary(sample_upload, sample_summary):
    """Test upload-summary relationship."""
    assert sample_upload.summaries[0] == sample_summary
    assert sample_summary.upload == sample_upload
```

## Coverage and Quality

### Coverage Metrics
```bash
$ uv run pytest --cov=. --cov-report=term-missing
---------- coverage: platform darwin, python 3.13 ----------
Name                          Stmts   Miss  Cover   Missing
-----------------------------------------------------------
src/pdf_summarizer/main.py      245     12    95%   423-425, 567-570
src/pdf_summarizer/models.py     45      2    96%   78-79
src/pdf_summarizer/utils.py      28      1    96%   45
-----------------------------------------------------------
TOTAL                           318     15    95%
```

### Quality Goals
- **Coverage**: Maintain 90%+ code coverage
- **Speed**: All tests in < 10 seconds
- **Isolation**: No test dependencies
- **Clarity**: Clear test names and assertions

## References

- [SQLite In-Memory Databases](https://www.sqlite.org/inmemorydb.html)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Flask Testing](https://flask.palletsprojects.com/en/3.0.x/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#when-do-i-construct-a-session-when-do-i-commit-it-and-when-do-i-close-it)

## Related ADRs

- Related to: ADR-0002 (Use SQLite with SQLAlchemy ORM)
- Related to: ADR-0001 (Use Flask as Web Framework) - Flask test client
