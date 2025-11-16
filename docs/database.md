# Database Schema Documentation

This document provides a comprehensive overview of the PDF Summarizer database schema, including tables, relationships, indexes, and usage patterns.

## Overview

The PDF Summarizer application uses **SQLite** as its default database engine, managed through **Flask-SQLAlchemy** ORM. The database stores uploaded PDF files metadata, their summaries, and tracks user sessions for caching and rate limiting.

### Database Configuration

- **Default URI**: `sqlite:///pdf_summaries.db` (relative to application root)
- **Environment Variable**: `DATABASE_URL`
- **CLI Override**: `--database` flag
- **Location**: Root directory (configurable via `DATABASE_URL`)
- **ORM**: Flask-SQLAlchemy
- **Migration Tool**: Flask-Migrate (Alembic)

### Key Features

- **Session-based tracking**: UUIDs for anonymous user sessions (30-day lifetime)
- **Caching support**: SHA256 file hash deduplication for cost reduction
- **Cascade deletion**: Automatic cleanup of summaries when uploads are deleted
- **Indexed lookups**: Optimized queries for file hash and session ID
- **Automated cleanup**: Scheduled deletion of old uploads and orphaned files

---

## Database Tables

### Table: `upload`

Stores metadata about uploaded PDF files.

#### Columns

| Column Name         | Type          | Nullable | Default                 | Indexed | Description |
|---------------------|---------------|----------|-------------------------|---------|-------------|
| `id`                | INTEGER       | No       | Auto-increment          | PK      | Primary key, unique identifier for each upload |
| `filename`          | VARCHAR(255)  | No       | -                       | No      | Secure filename stored on disk (timestamped) |
| `original_filename` | VARCHAR(255)  | No       | -                       | No      | Original filename from user upload |
| `file_path`         | VARCHAR(500)  | No       | -                       | No      | Full path to stored PDF file |
| `file_hash`         | VARCHAR(64)   | Yes      | NULL                    | Yes     | SHA256 hash of file content for caching (allows duplicates) |
| `session_id`        | VARCHAR(255)  | Yes      | NULL                    | Yes     | User session UUID for tracking uploads |
| `upload_date`       | DATETIME      | No       | `datetime.now(UTC)`     | No      | Timestamp when file was uploaded (UTC) |
| `file_size`         | INTEGER       | Yes      | NULL                    | No      | File size in bytes |
| `is_cached`         | BOOLEAN       | No       | `False`                 | No      | Whether this upload was a cache hit (summary reused) |

#### Indexes

- **Primary Key**: `id`
- **Index on `file_hash`**: For fast cache lookups by file content hash
- **Index on `session_id`**: For efficient user session queries

#### Constraints

- `filename`, `original_filename`, `file_path` are NOT NULL
- `file_hash` allows multiple entries with the same hash (for caching different uploads of identical files)

#### Relationships

- **One-to-Many** with `summary`: One upload can have multiple summaries
  - Relationship name: `upload.summaries`
  - Cascade: `all, delete-orphan` (deleting an upload deletes all its summaries)
  - Backref: `summary.upload`

#### Example Data

```sql
INSERT INTO upload (filename, original_filename, file_path, file_hash, session_id, file_size, is_cached)
VALUES (
    'report_20251116_143022.pdf',
    'quarterly_report.pdf',
    'uploads/report_20251116_143022.pdf',
    'a3b2c1d4e5f6789012345678901234567890abcdef1234567890abcdef123456',
    '550e8400-e29b-41d4-a716-446655440000',
    2048576,
    0
);
```

---

### Table: `summary`

Stores AI-generated summaries for uploaded PDF files.

#### Columns

| Column Name    | Type     | Nullable | Default              | Indexed | Description |
|----------------|----------|----------|----------------------|---------|-------------|
| `id`           | INTEGER  | No       | Auto-increment       | PK      | Primary key, unique identifier for each summary |
| `upload_id`    | INTEGER  | No       | -                    | FK      | Foreign key to `upload.id` |
| `summary_text` | TEXT     | No       | -                    | No      | Generated summary content (unlimited length) |
| `created_date` | DATETIME | No       | `datetime.now(UTC)`  | No      | Timestamp when summary was created (UTC) |
| `page_count`   | INTEGER  | Yes      | NULL                 | No      | Number of pages in the PDF |
| `char_count`   | INTEGER  | Yes      | NULL                 | No      | Character count of extracted text |

#### Indexes

- **Primary Key**: `id`
- **Foreign Key**: `upload_id` references `upload.id`

#### Constraints

- `upload_id` and `summary_text` are NOT NULL
- Foreign key constraint with **CASCADE DELETE** (deleting parent upload deletes summaries)

#### Relationships

- **Many-to-One** with `upload`: Each summary belongs to one upload
  - Foreign key: `upload_id`
  - Backref: `summary.upload` (access parent upload)
  - Parent relationship: `upload.summaries` (list of summaries)

#### Example Data

```sql
INSERT INTO summary (upload_id, summary_text, page_count, char_count)
VALUES (
    1,
    'This quarterly report covers Q4 2024 financial performance. Key highlights include 15% revenue growth, successful product launches, and expansion into new markets. The report details financial statements, operational metrics, and strategic initiatives.',
    24,
    45678
);
```

---

## Entity-Relationship Diagram

```
┌─────────────────────────┐
│       upload            │
├─────────────────────────┤
│ id (PK)                 │
│ filename                │
│ original_filename       │
│ file_path               │
│ file_hash (indexed)     │
│ session_id (indexed)    │
│ upload_date             │
│ file_size               │
│ is_cached               │
└───────────┬─────────────┘
            │
            │ 1:N
            │ cascade delete
            │
            ▼
┌─────────────────────────┐
│       summary           │
├─────────────────────────┤
│ id (PK)                 │
│ upload_id (FK)          │
│ summary_text            │
│ created_date            │
│ page_count              │
│ char_count              │
└─────────────────────────┘
```

---

## Database Operations

### Common Queries

#### 1. Find Upload by File Hash (Cache Lookup)

```python
from pdf_summarizer.models import Upload, Summary, db

# Check if file has been processed before
existing_upload = Upload.query.filter_by(file_hash="abc123...").first()

if existing_upload and existing_upload.summaries:
    # Cache hit - reuse existing summary
    cached_summary = existing_upload.summaries[0]
```

#### 2. Get User's Recent Uploads

```python
# Get uploads for current session, ordered by date
session_id = "550e8400-e29b-41d4-a716-446655440000"
uploads = Upload.query.filter_by(session_id=session_id)\
                      .order_by(Upload.upload_date.desc())\
                      .limit(10)\
                      .all()
```

#### 3. Create Upload with Summary

```python
from datetime import datetime, UTC

# Create new upload
upload = Upload(
    filename="secure_20251116_143022.pdf",
    original_filename="document.pdf",
    file_path="uploads/secure_20251116_143022.pdf",
    file_hash="abc123...",
    session_id=session_id,
    file_size=1024000,
    is_cached=False
)
db.session.add(upload)
db.session.flush()  # Get upload.id

# Create associated summary
summary = Summary(
    upload_id=upload.id,
    summary_text="AI-generated summary...",
    page_count=10,
    char_count=25000
)
db.session.add(summary)
db.session.commit()
```

#### 4. Delete Old Uploads (Cleanup)

```python
from datetime import timedelta

cutoff_date = datetime.now(UTC) - timedelta(days=30)

# Delete uploads older than 30 days (summaries cascade delete)
old_uploads = Upload.query.filter(Upload.upload_date < cutoff_date).all()
for upload in old_uploads:
    db.session.delete(upload)  # Summaries auto-deleted
db.session.commit()
```

#### 5. Count Cache Hits

```python
# Statistics query
total_uploads = Upload.query.count()
cache_hits = Upload.query.filter_by(is_cached=True).count()
cache_rate = (cache_hits / total_uploads) * 100 if total_uploads > 0 else 0
```

---

## Caching Mechanism

### How File Hash Caching Works

1. **File Upload**: User uploads a PDF file
2. **Hash Calculation**: SHA256 hash computed from file content
3. **Cache Lookup**: Query database for existing upload with same `file_hash`
4. **Cache Hit**:
   - Existing summary found
   - Create new upload record with `is_cached=True`
   - Reuse summary from cached upload
   - **No API call to Claude** (cost savings)
5. **Cache Miss**:
   - No existing summary found
   - Create upload with `is_cached=False`
   - Call Claude API to generate summary
   - Store new summary

### Cache Benefits

- **60% potential cost reduction** for duplicate PDFs
- Cross-session caching (different users benefit)
- Prevents redundant API calls
- Faster processing for duplicate files

### Database Impact

```sql
-- Cache lookup query (indexed on file_hash)
SELECT * FROM upload
WHERE file_hash = 'abc123...'
LIMIT 1;

-- If found, get summary
SELECT * FROM summary
WHERE upload_id = <cached_upload_id>
LIMIT 1;
```

---

## Session Management

### Session Tracking

- **Session ID**: UUID v4 string (36 characters)
- **Lifetime**: 30 days (configurable via `SESSION_LIFETIME_DAYS`)
- **Storage**: Flask session cookie (signed, HTTP-only)
- **Purpose**: Track uploads per user without authentication

### Session-Based Queries

```python
# User's own uploads (My Uploads page)
my_uploads = Upload.query.filter_by(session_id=current_session_id)\
                         .order_by(Upload.upload_date.desc())\
                         .all()

# Count uploads for rate limiting
session_upload_count = Upload.query.filter_by(session_id=current_session_id)\
                                    .filter(Upload.upload_date > one_hour_ago)\
                                    .count()
```

---

## Cascade Deletion

### Upload → Summary Cascade

When an upload is deleted, all associated summaries are **automatically deleted** via cascade.

```python
# This configuration in Upload model:
summaries = db.relationship(
    "Summary",
    backref="upload",
    lazy=True,
    cascade="all, delete-orphan"
)

# Deleting an upload:
upload = Upload.query.get(upload_id)
db.session.delete(upload)
db.session.commit()
# → All summary records with upload_id=upload_id are deleted
```

### File System Cleanup

**Important**: Cascade deletion only affects database records. Physical PDF files in the `uploads/` folder must be deleted separately:

```python
import os

upload = Upload.query.get(upload_id)
file_path = upload.file_path

# Delete from database (cascades to summaries)
db.session.delete(upload)
db.session.commit()

# Delete physical file
if os.path.exists(file_path):
    os.remove(file_path)
```

---

## Database Initialization

### First Run

The database is automatically created when the application starts:

```python
# In main.py
with app.app_context():
    db.create_all()  # Creates tables if they don't exist
```

### Manual Database Creation

```bash
# Using Flask shell
flask shell

>>> from pdf_summarizer.models import db
>>> db.create_all()
>>> exit()
```

### Reset Database

```bash
# Delete database file
rm pdf_summaries.db

# Restart application (auto-creates tables)
make run
```

---

## Database Migrations

### Using Flask-Migrate (Alembic)

For schema changes in production:

```bash
# Initialize migrations (first time only)
flask db init

# Create migration after model changes
flask db migrate -m "Add new column to upload table"

# Review generated migration file
# migrations/versions/xxxxx_add_new_column.py

# Apply migration
flask db upgrade

# Rollback if needed
flask db downgrade
```

### Migration Example: Adding a Column

```python
# 1. Modify model in main.py
class Upload(db.Model):
    # ... existing columns ...
    download_count = db.Column(db.Integer, default=0)  # New column

# 2. Generate migration
# flask db migrate -m "Add download_count to upload"

# 3. Apply migration
# flask db upgrade
```

---

## Database Constraints & Validation

### Column Constraints

1. **NOT NULL**:
   - `upload.filename`, `upload.original_filename`, `upload.file_path`
   - `summary.upload_id`, `summary.summary_text`

2. **Foreign Keys**:
   - `summary.upload_id` → `upload.id` (with CASCADE DELETE)

3. **Defaults**:
   - `upload.upload_date`: Current UTC timestamp
   - `upload.is_cached`: `False`
   - `summary.created_date`: Current UTC timestamp

### Application-Level Validation

```python
# File size validation (in UploadForm)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# File type validation
ALLOWED_EXTENSIONS = ['pdf']

# Text length validation
MAX_TEXT_LENGTH = 100000  # ~100k characters
```

---

## Performance Considerations

### Indexes

The database uses indexes for frequently queried columns:

1. **`upload.file_hash`**: Fast cache lookups (O(log n))
2. **`upload.session_id`**: Efficient session-based queries
3. **`upload.id`** (PK): Fast primary key lookups
4. **`summary.upload_id`** (FK): Fast join operations

### Query Optimization

```python
# Good: Use indexed columns
uploads = Upload.query.filter_by(file_hash=hash_value).first()

# Good: Limit results for large datasets
recent = Upload.query.order_by(Upload.upload_date.desc()).limit(10).all()

# Good: Use relationships (single query with join)
upload = Upload.query.get(upload_id)
summaries = upload.summaries  # No additional query

# Avoid: N+1 queries
# Bad
uploads = Upload.query.all()
for upload in uploads:
    print(upload.summaries)  # N additional queries

# Good
uploads = Upload.query.options(db.joinedload(Upload.summaries)).all()
```

### Database Size

Typical storage requirements:

- **Upload record**: ~500 bytes (metadata only)
- **Summary record**: 500-5000 bytes (depending on summary length)
- **PDF file**: 100KB - 10MB (stored in file system, not database)

For 1,000 uploads with summaries:
- **Database size**: ~1-5 MB
- **File system**: 100MB - 10GB

---

## Backup & Recovery

### SQLite Backup

```bash
# Copy database file (application must be stopped)
cp pdf_summaries.db pdf_summaries_backup_$(date +%Y%m%d).db

# Or use SQLite .backup command (while running)
sqlite3 pdf_summaries.db ".backup pdf_summaries_backup.db"
```

### Restore

```bash
# Stop application
# Replace database file
cp pdf_summaries_backup.db pdf_summaries.db
# Restart application
```

### Full Application Backup

Must include both database and uploads:

```bash
# Backup script
tar -czf backup_$(date +%Y%m%d).tar.gz \
    pdf_summaries.db \
    uploads/
```

---

## Testing

The database is mocked in tests using **in-memory SQLite**:

```python
# In tests/conftest.py
@pytest.fixture
def app():
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
```

Benefits:
- **Fast**: In-memory operations
- **Isolated**: Each test gets fresh database
- **No cleanup**: Automatically destroyed after tests

---

## Related Files

- **Models**: [src/pdf_summarizer/models.py](../src/pdf_summarizer/models.py) - Database model definitions
- **Config**: [src/pdf_summarizer/config.py:22](../src/pdf_summarizer/config.py#L22) - Database URI configuration
- **Tests**: [tests/test_models.py](../tests/test_models.py) - Model and relationship tests
- **Migration**: Use Flask-Migrate for schema changes in production

---

**Last Updated**: 2025-11-16
**Database Version**: SQLite 3.x
**ORM**: Flask-SQLAlchemy 3.1+
