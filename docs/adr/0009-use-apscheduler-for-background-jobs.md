# ADR-0009: Use APScheduler for Background Cleanup Jobs

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: Automated cleanup of old uploads and summaries

## Context

The PDF Summarizer accumulates uploaded files and database records over time. Without cleanup, storage grows indefinitely. The application needs a mechanism to:

- Delete uploads older than retention period (default 30 days)
- Remove associated database records
- Delete orphaned PDF files from filesystem
- Run cleanup automatically on a schedule
- Execute in background without blocking web requests

Key requirements:
- **Automated execution**: Run daily without manual intervention
- **Configurable schedule**: Allow customization of cleanup time
- **Reliable execution**: Handle errors and retries
- **Minimal overhead**: Lightweight, doesn't impact web performance
- **Easy integration**: Works within Flask monolith

## Decision

Use **APScheduler** (Advanced Python Scheduler) with `BackgroundScheduler` to run automated cleanup jobs.

APScheduler provides:
- **Background execution**: Runs in separate thread, doesn't block web server
- **Flexible scheduling**: Cron-like expressions, intervals, date-based triggers
- **Job persistence**: Can persist jobs across restarts (optional)
- **Error handling**: Built-in retry and exception handling
- **Pythonic API**: Simple decorator-based job registration
- **No external dependencies**: Pure Python, no Redis/Celery required

### Implementation
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def cleanup_old_uploads():
    """Delete uploads older than retention period."""
    cutoff_date = datetime.now() - timedelta(days=config.RETENTION_DAYS)
    old_uploads = Upload.query.filter(Upload.upload_date < cutoff_date).all()
    for upload in old_uploads:
        os.remove(upload.file_path)
        db.session.delete(upload)
    db.session.commit()

# Schedule daily at 3 AM
scheduler.add_job(
    cleanup_old_uploads,
    trigger='cron',
    hour=3,
    minute=0,
    id='cleanup_job'
)
scheduler.start()
```

## Alternatives Considered

### Alternative 1: Celery + Redis
- **Description**: Distributed task queue with message broker
- **Pros**:
  - Industry standard for background jobs
  - Distributed execution across workers
  - Advanced features (retries, rate limiting, chains)
  - Monitoring tools (Flower)
  - Can scale to millions of tasks
- **Cons**:
  - Requires Redis/RabbitMQ (additional infrastructure)
  - Complex setup and configuration
  - Overkill for simple daily cleanup
  - Higher operational overhead
  - More dependencies to manage
  - Deployment complexity (separate worker process)
- **Rejected because**: PDF Summarizer only needs simple scheduled cleanup. Celery requires Redis infrastructure and separate worker processes. APScheduler runs in-process with zero additional setup.

### Alternative 2: Cron Job + External Script
- **Description**: System cron job calling Python script
- **Pros**:
  - Standard Unix scheduling mechanism
  - Separate from application (isolation)
  - Easy to monitor with cron logs
  - No Python dependencies
  - Can run even if app is down
- **Cons**:
  - Requires system access to configure cron
  - Not portable across OS (Windows different)
  - Separate script needs database access
  - Configuration outside application code
  - Hard to deploy (manual cron setup)
  - Not testable with application
  - Environment variables must be replicated
- **Rejected because**: Requires system-level configuration. Not portable (Windows users must use Task Scheduler). Deployment becomes more complex. APScheduler keeps everything in application code.

### Alternative 3: Flask-APScheduler Extension
- **Description**: Flask-specific wrapper around APScheduler
- **Pros**:
  - Flask integration (app context, config)
  - Blueprint support
  - REST API for job management (optional)
  - Flask configuration integration
- **Cons**:
  - Extra dependency (flask-apscheduler)
  - Limited benefits over raw APScheduler
  - One more layer of abstraction
  - Less flexible than direct APScheduler
  - Not actively maintained
- **Rejected because**: Direct APScheduler is simple enough. Flask-APScheduler adds minimal value while introducing another dependency. Can access Flask `app` context manually if needed.

### Alternative 4: Systemd Timer (Linux only)
- **Description**: Use systemd timer units instead of cron
- **Pros**:
  - Modern alternative to cron (on Linux)
  - Better logging and monitoring
  - Dependency management
  - Resource limits
- **Cons**:
  - Linux-only (not portable)
  - Requires root/systemd access
  - Complex configuration files
  - Outside application code
  - Not suitable for shared hosting
- **Rejected because**: Not portable. Requires system-level configuration. APScheduler is Python-based and works everywhere.

### Alternative 5: Manual Cleanup (No Automation)
- **Description**: Rely on users/admins to run cleanup manually
- **Pros**:
  - No background job infrastructure needed
  - Simplest possible approach
  - Complete control over timing
- **Cons**:
  - Easy to forget (storage fills up)
  - Poor user experience
  - Requires manual intervention
  - Not scalable
  - Defeats purpose of automation
- **Rejected because**: Manual cleanup is unreliable. Storage will grow indefinitely without automation. Users should not need to manage cleanup.

## Consequences

### Positive Consequences
- **Fully automated**: Cleanup runs without human intervention
- **Zero infrastructure**: No Redis, no cron, no external services
- **Simple deployment**: Part of Flask app, no separate worker
- **Portable**: Works on Windows, Linux, macOS
- **Configurable**: Easy to change schedule and retention period
- **Testable**: Can trigger cleanup in tests
- **Lightweight**: Minimal memory overhead (background thread)
- **Reliable**: Built-in error handling and logging

### Negative Consequences
- **Single-process limitation**: Only runs if Flask app is running
- **No distributed execution**: Cannot scale across multiple workers
- **In-process**: Cleanup competes for CPU with web requests (minimal impact)
- **No persistence**: Jobs lost if scheduler not configured to persist
- **Limited monitoring**: No built-in UI (use logging instead)
- **Thread-based**: Subject to Python GIL (acceptable for I/O-bound cleanup)

### Neutral Consequences
- **Daily execution**: Configurable but defaults to 3 AM
- **Error handling**: Must implement custom retry logic if needed
- **Logging**: Must configure logging for job execution

## Implementation Notes

### Scheduler Setup
```python
# src/pdf_summarizer/main.py
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def setup_scheduler(app):
    """Configure and start background scheduler."""
    cleanup_hour = app.config.get('CLEANUP_HOUR', 3)

    scheduler.add_job(
        func=cleanup_old_uploads,
        trigger='cron',
        hour=cleanup_hour,
        minute=0,
        id='cleanup_job',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Scheduler started. Cleanup runs daily at {cleanup_hour}:00")

    # Shutdown scheduler on app exit
    import atexit
    atexit.register(lambda: scheduler.shutdown())
```

### Cleanup Job
```python
def cleanup_old_uploads():
    """Delete uploads older than retention period."""
    with app.app_context():  # Flask app context for database access
        try:
            cutoff_date = datetime.now() - timedelta(days=config.RETENTION_DAYS)
            old_uploads = Upload.query.filter(Upload.upload_date < cutoff_date).all()

            count = 0
            for upload in old_uploads:
                # Delete file from filesystem
                if os.path.exists(upload.file_path):
                    os.remove(upload.file_path)
                    logger.info(f"Deleted file: {upload.file_path}")

                # Delete database record
                db.session.delete(upload)
                count += 1

            db.session.commit()
            logger.info(f"Cleanup completed: {count} uploads deleted")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            db.session.rollback()
```

### Configuration
```python
# src/pdf_summarizer/config.py
RETENTION_DAYS = int(os.getenv('RETENTION_DAYS', '30'))
CLEANUP_HOUR = int(os.getenv('CLEANUP_HOUR', '3'))
```

### Code Locations
- Scheduler setup: [src/pdf_summarizer/main.py:92-108](../../src/pdf_summarizer/main.py#L92-L108)
- Cleanup job: [src/pdf_summarizer/main.py:113-136](../../src/pdf_summarizer/main.py#L113-L136)
- Configuration: [src/pdf_summarizer/config.py:40-41](../../src/pdf_summarizer/config.py#L40-L41)

### Testing
```python
# tests/test_cleanup.py
def test_cleanup_old_uploads(app, db):
    """Test cleanup job deletes old uploads."""
    # Create old upload
    old_date = datetime.now() - timedelta(days=40)
    upload = Upload(upload_date=old_date, ...)
    db.session.add(upload)
    db.session.commit()

    # Run cleanup
    cleanup_old_uploads()

    # Verify deletion
    assert Upload.query.get(upload.id) is None
```

## Scheduling Options

### Daily Cleanup (Default)
```python
scheduler.add_job(cleanup_old_uploads, trigger='cron', hour=3, minute=0)
```

### Interval-Based
```python
# Run every 6 hours
scheduler.add_job(cleanup_old_uploads, trigger='interval', hours=6)
```

### One-Time Execution
```python
# Run at specific date/time
scheduler.add_job(cleanup_old_uploads, trigger='date', run_date='2025-12-01 03:00:00')
```

### Cron Expression
```python
# Run Monday-Friday at 3 AM
scheduler.add_job(cleanup_old_uploads, trigger='cron', day_of_week='mon-fri', hour=3)
```

## Performance Considerations

### Cleanup Performance
- **Query**: Indexed on `upload_date` for fast filtering
- **Deletion**: Batch delete in single transaction
- **File I/O**: Sequential file deletion (no parallelization needed)
- **Typical duration**: 1-10 seconds for 1000 uploads

### Impact on Web Server
- **Runs in background thread**: Doesn't block web requests
- **Database locks**: SQLite locks during commit (brief)
- **CPU usage**: Minimal (I/O-bound operation)
- **Memory**: Small (processes records in chunks)

### Optimization
```python
# If cleanup becomes slow, process in chunks
def cleanup_old_uploads():
    batch_size = 100
    while True:
        old_uploads = Upload.query.filter(...).limit(batch_size).all()
        if not old_uploads:
            break
        for upload in old_uploads:
            # Delete...
        db.session.commit()
```

## Monitoring and Logging

### Logging
```python
logger.info(f"Cleanup started. Retention: {config.RETENTION_DAYS} days")
logger.info(f"Deleted file: {upload.file_path}")
logger.info(f"Cleanup completed: {count} uploads deleted")
logger.error(f"Cleanup failed: {e}")
```

### Metrics
```python
def cleanup_old_uploads():
    start_time = time.time()
    # ... cleanup logic ...
    duration = time.time() - start_time
    logger.info(f"Cleanup took {duration:.2f} seconds")
```

## References

- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [BackgroundScheduler](https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/background.html)
- [Cron Triggers](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html)

## Related ADRs

- Related to: ADR-0005 (Monolithic Application Architecture)
- Related to: ADR-0008 (Store PDF Files on Filesystem)
