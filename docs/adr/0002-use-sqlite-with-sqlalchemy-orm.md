# ADR-0002: Use SQLite with SQLAlchemy ORM

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: Database architecture for storing upload metadata and summaries

## Context

The PDF Summarizer needs to persist data about:
- Uploaded PDF files (metadata, not binary content)
- AI-generated summaries
- User session tracking for caching
- File hashes for deduplication

Requirements:
- Store structured relational data (uploads, summaries with foreign keys)
- Simple deployment (no separate database server)
- ACID transactions for data integrity
- Support for migrations as schema evolves
- Fast local development without external dependencies
- Query flexibility for cache lookups and session filtering

The application is intended for:
- Single-server deployment
- Low to moderate traffic (< 1000 users)
- Simple data model (2-3 tables)
- Development/educational use case

## Decision

Use **SQLite** as the database engine with **Flask-SQLAlchemy** (SQLAlchemy ORM).

### Database Engine: SQLite
- File-based database (`pdf_summaries.db`)
- No separate server process required
- ACID-compliant transactions
- Full SQL support for queries and indexes

### ORM: SQLAlchemy via Flask-SQLAlchemy
- Declarative models for Upload and Summary tables
- Relationship management with cascade deletion
- Query builder for complex lookups
- Migration support via Flask-Migrate (Alembic)

## Alternatives Considered

### Alternative 1: PostgreSQL
- **Description**: Production-grade relational database
- **Pros**:
  - Better concurrency handling
  - More advanced features (full-text search, JSON columns)
  - Better performance at scale
  - Industry standard for web applications
  - Connection pooling
- **Cons**:
  - Requires separate database server
  - More complex deployment and configuration
  - Overkill for simple data model
  - Additional operational overhead
  - Not suitable for educational/demo purposes
- **Rejected because**: Added complexity not justified for this use case. Single-file SQLite database is simpler to deploy, backup, and share. No high-concurrency requirements.

### Alternative 2: MySQL/MariaDB
- **Description**: Popular open-source relational database
- **Pros**:
  - Well-documented and widely used
  - Good performance
  - Strong community support
- **Cons**:
  - Requires separate server process
  - More complex deployment
  - Connection management overhead
  - Not as simple as SQLite for small applications
- **Rejected because**: Same reasoning as PostgreSQL. Unnecessary complexity for our data scale and access patterns.

### Alternative 3: MongoDB (NoSQL)
- **Description**: Document-oriented NoSQL database
- **Pros**:
  - Schema-less flexibility
  - Good for unstructured data
  - Horizontal scaling
- **Cons**:
  - Poor fit for relational data (upload-summary relationship)
  - No ACID transactions (in older versions)
  - Requires separate server
  - Unfamiliar query language
  - No JOIN support
- **Rejected because**: Our data is clearly relational (uploads have summaries, foreign key relationships). SQLite's relational model is a better fit.

### Alternative 4: Direct SQL with sqlite3 module
- **Description**: Use Python's built-in sqlite3 without ORM
- **Pros**:
  - No external dependencies
  - Full control over queries
  - Slightly better performance
- **Cons**:
  - Manual SQL string construction (SQL injection risk)
  - No automatic migrations
  - No relationship management
  - More boilerplate code
  - Harder to maintain and test
- **Rejected because**: SQLAlchemy provides significant productivity benefits (automatic migrations, relationship handling, query builder) with minimal overhead. The abstraction is worth the small performance trade-off.

## Consequences

### Positive Consequences
- **Zero configuration**: No database server to install or configure
- **Portable**: Single file database easy to backup and share
- **Simple deployment**: Copy `.db` file with application code
- **ACID compliance**: Data integrity guaranteed
- **Fast development**: No connection setup or authentication
- **Testing**: In-memory SQLite (`sqlite:///:memory:`) enables fast isolated tests
- **ORM benefits**: Type-safe queries, relationship management, automatic migrations
- **Low resource usage**: No separate database process consuming memory/CPU

### Negative Consequences
- **Limited concurrency**: SQLite locks entire database for writes (acceptable for our use case)
- **No network access**: Database must be on same server as application
- **Scaling limitations**: Not suitable for high-traffic applications
- **Missing features**: No stored procedures, limited text search, no user management
- **File corruption risk**: Single file corruption affects entire database

### Neutral Consequences
- **File-based storage**: Database lives in application directory
- **Backup simplicity**: Just copy the `.db` file
- **Migration path**: Can migrate to PostgreSQL later if needed (SQLAlchemy abstracts engine)

## Implementation Notes

### Database Configuration
```python
# In config.py
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///pdf_summaries.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
```

### Model Definition
```python
# In main.py
class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_hash = db.Column(db.String(64), index=True)  # SHA256 hash
    session_id = db.Column(db.String(255), index=True)
    summaries = db.relationship("Summary", backref="upload", lazy=True,
                                cascade="all, delete-orphan")

class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("upload.id"), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
```

### Code Locations
- Database models: [src/pdf_summarizer/main.py:91-121](../../src/pdf_summarizer/main.py#L91-L121)
- Configuration: [src/pdf_summarizer/config.py:22-23](../../src/pdf_summarizer/config.py#L22-L23)
- Initialization: [src/pdf_summarizer/main.py:496](../../src/pdf_summarizer/main.py#L496)

### Database Schema
See [docs/database.md](../database.md) for complete schema documentation.

### Testing Strategy
Tests use in-memory SQLite for isolation and speed:
```python
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
```

## References

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- [When to Use SQLite](https://www.sqlite.org/whentouse.html)
- [Database Schema Documentation](../database.md)

## Related ADRs

- Related to: ADR-0001 (Use Flask as Web Framework)
- Related to: ADR-0006 (SHA256 Hash-Based Caching)
- Related to: ADR-0012 (In-Memory SQLite for Testing)
