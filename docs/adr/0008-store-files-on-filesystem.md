# ADR-0008: Store PDF Files on Filesystem, Not Database

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: PDF file storage strategy

## Context

The PDF Summarizer uploads PDF files that need to be stored for record-keeping and potential re-processing. The application must decide where to store these binary files: in the database as BLOBs or on the filesystem as files.

Key considerations:
- **File sizes**: PDFs typically 1-10MB, occasionally up to 20MB
- **Upload volume**: 100-1000 uploads/day expected
- **Access patterns**: Files read once for text extraction, rarely accessed again
- **Retention**: Files stored for 30 days before automatic cleanup
- **Database**: SQLite (file-based, not designed for large BLOBs)
- **Deployment**: Single server with local storage

## Decision

Store uploaded PDF files on the **filesystem** in an `uploads/` directory, with only file metadata (path, size, hash) in the database.

### Storage Strategy
- **Filesystem**: Store actual PDF files in `uploads/` directory
- **Database**: Store file metadata (filename, path, size, hash, upload_date)
- **Naming**: Use UUID-based filenames to avoid collisions
- **Organization**: Flat directory structure (no subdirectories)
- **Cleanup**: Automated deletion of files older than retention period

### Database Schema
```sql
CREATE TABLE upload (
    id INTEGER PRIMARY KEY,
    filename VARCHAR(255),        -- Original filename
    file_path VARCHAR(500),       -- Path to file on disk
    file_size INTEGER,            -- Size in bytes
    file_hash VARCHAR(64),        -- SHA256 hash
    upload_date DATETIME,
    ...
);
```

### File Storage
```python
# Save uploaded file
upload_dir = "uploads"
unique_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
file_path = os.path.join(upload_dir, unique_filename)
file.save(file_path)

# Store metadata in database
upload = Upload(
    filename=file.filename,
    file_path=file_path,
    file_size=os.path.getsize(file_path)
)
```

## Alternatives Considered

### Alternative 1: Store PDFs as Database BLOBs
- **Description**: Store entire PDF content in SQLite BLOB column
- **Pros**:
  - Single storage location (database contains everything)
  - Atomic transactions (file and metadata always in sync)
  - Easier backup (single database file)
  - No filesystem permission issues
  - Database handles file integrity
- **Cons**:
  - SQLite not optimized for large BLOBs (degrades performance)
  - Database file grows very large (100MB for 10 PDFs)
  - Increased memory usage (entire file loaded into RAM)
  - Slower backups (database file is huge)
  - Difficult to inspect files manually
  - SQLite has 1GB page size limit (can hit with large BLOBs)
  - Database queries slower when table has large BLOBs
- **Rejected because**: SQLite performs poorly with large BLOBs. Database file would grow from KB to GB quickly. Filesystem storage is more efficient for binary files.

### Alternative 2: Object Storage (AWS S3)
- **Description**: Store PDFs in cloud object storage (S3, Google Cloud Storage)
- **Pros**:
  - Unlimited scalability
  - Built-in redundancy and durability
  - Geographic distribution
  - No disk space management
  - Lifecycle policies for automatic deletion
  - Versioning support
- **Cons**:
  - Requires cloud provider account
  - Network latency for file access
  - Additional costs ($0.023/GB/month + transfer)
  - More complex deployment
  - Internet connectivity required
  - API calls add latency
  - Overkill for local deployment
- **Rejected because**: Local filesystem sufficient for current scale. Cloud storage adds cost and complexity without benefits. Deployment goal is simple self-hosting.

### Alternative 3: Network File System (NFS/SMB)
- **Description**: Store files on network-attached storage
- **Pros**:
  - Centralized storage
  - Easy to share across servers
  - Better backup infrastructure
  - Can scale storage independently
- **Cons**:
  - Network latency for file operations
  - Requires NFS/SMB server setup
  - Single point of failure (network)
  - More complex deployment
  - Not needed for single-server deployment
- **Rejected because**: Monolithic architecture runs on single server. Network storage adds complexity and latency without scaling benefits.

### Alternative 4: Hybrid (Small Files in DB, Large Files on Disk)
- **Description**: Store PDFs <1MB in database, larger files on filesystem
- **Pros**:
  - Small files benefit from database performance
  - Large files don't bloat database
  - Flexible approach
- **Cons**:
  - Complex logic (two storage paths)
  - Hard to maintain (special cases)
  - Difficult to test both paths
  - Arbitrary threshold (what is "small"?)
  - Increased code complexity
  - Inconsistent storage model
- **Rejected because**: Added complexity not worth minor benefits. Simpler to have single storage strategy. Filesystem works well for all file sizes.

## Consequences

### Positive Consequences
- **Better performance**: Filesystem optimized for binary files
- **Smaller database**: Database stays small and fast (only metadata)
- **Easy inspection**: Can manually view/delete files in uploads/ directory
- **Fast backups**: Database backup is fast (only metadata)
- **No size limits**: Filesystem can handle any PDF size
- **Efficient cleanup**: Delete files without vacuuming database
- **Simple implementation**: Standard file I/O operations

### Negative Consequences
- **Two storage locations**: Database and filesystem must stay in sync
- **Orphaned files**: Deleted database records may leave files on disk (mitigated by cleanup job)
- **Manual cleanup**: Must delete both database record AND file
- **Filesystem permissions**: Must configure directory permissions correctly
- **Backup complexity**: Must backup both database and uploads/ directory
- **No atomic operations**: File deletion not atomic with database deletion

### Neutral Consequences
- **Disk space management**: Must monitor uploads/ directory size
- **Path handling**: Must handle file paths correctly (OS-specific)
- **Migration**: Moving servers requires copying uploads/ directory

## Implementation Notes

### Directory Structure
```
pdf-summarizer/
├── uploads/                    # PDF file storage
│   ├── abc123-document.pdf
│   ├── def456-report.pdf
│   └── ghi789-paper.pdf
├── pdf_summaries.db            # Database (metadata only)
└── src/pdf_summarizer/
    └── main.py
```

### File Upload Handling
```python
# src/pdf_summarizer/main.py
import os
import uuid
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['pdf']

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    # Save to filesystem
    file.save(file_path)

    # Store metadata in database
    upload = Upload(
        filename=file.filename,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        file_hash=calculate_file_hash(open(file_path, 'rb').read())
    )
    db.session.add(upload)
    db.session.commit()
```

### File Deletion
```python
def delete_upload(upload_id):
    upload = Upload.query.get(upload_id)
    if upload:
        # Delete file from filesystem
        if os.path.exists(upload.file_path):
            os.remove(upload.file_path)

        # Delete database record
        db.session.delete(upload)
        db.session.commit()
```

### Cleanup Job
```python
def cleanup_old_uploads():
    """Delete uploads older than retention period."""
    cutoff_date = datetime.now() - timedelta(days=config.RETENTION_DAYS)
    old_uploads = Upload.query.filter(Upload.upload_date < cutoff_date).all()

    for upload in old_uploads:
        # Delete file from filesystem
        if os.path.exists(upload.file_path):
            os.remove(upload.file_path)
            logger.info(f"Deleted file: {upload.file_path}")

        # Delete database record
        db.session.delete(upload)

    db.session.commit()
```

### Code Locations
- Upload handling: [src/pdf_summarizer/main.py:296-355](../../src/pdf_summarizer/main.py#L296-L355)
- Cleanup job: [src/pdf_summarizer/main.py:113-136](../../src/pdf_summarizer/main.py#L113-L136)
- Configuration: [src/pdf_summarizer/config.py:20-21](../../src/pdf_summarizer/config.py#L20-L21)

### Filesystem Configuration
```python
# src/pdf_summarizer/config.py
UPLOAD_FOLDER = "uploads"
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB max file size
```

### Directory Permissions
```bash
# Create uploads directory with correct permissions
mkdir -p uploads
chmod 755 uploads
```

## Security Considerations

### Filename Security
- Use `secure_filename()` from Werkzeug to sanitize filenames
- Add UUID prefix to prevent collisions and directory traversal
- Validate file extension (only .pdf allowed)

### Path Traversal Prevention
```python
from werkzeug.utils import secure_filename

# SAFE - secure_filename removes ../
filename = secure_filename(file.filename)  # "../../../etc/passwd" -> "etc_passwd"
```

### File Type Validation
```python
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

## Backup Strategy

### Full Backup
```bash
# Backup both database and files
tar -czf backup-$(date +%Y%m%d).tar.gz pdf_summaries.db uploads/
```

### Incremental Backup
```bash
# Backup only new files (last 24 hours)
find uploads/ -mtime -1 -type f | tar -czf incremental-$(date +%Y%m%d).tar.gz -T -
```

## References

- [SQLite BLOB Performance](https://www.sqlite.org/intern-v-extern-blob.html)
- [Werkzeug secure_filename](https://werkzeug.palletsprojects.com/en/3.0.x/utils/#werkzeug.utils.secure_filename)
- [File Upload Security](https://flask.palletsprojects.com/en/3.0.x/patterns/fileuploads/)

## Related ADRs

- Related to: ADR-0002 (Use SQLite with SQLAlchemy ORM)
- Related to: ADR-0005 (Monolithic Application Architecture)
- Related to: ADR-0009 (Use APScheduler for Background Cleanup Jobs)
