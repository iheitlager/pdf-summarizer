# ADR-0011: Multi-File Logging Strategy

**Status**: Accepted (Updated 2025-11-18)

**Date**: 2025-11-16 | **Last Updated**: 2025-11-18

**Technical Story**: Application observability and debugging

## Context

The PDF Summarizer requires comprehensive logging for debugging, monitoring, and audit trails. The application has several distinct logging needs:

- **Application logs**: General Flask app behavior, routes, errors
- **Error logs**: Critical errors requiring immediate attention
- **API logs**: External Claude API calls (cost tracking, latency monitoring)
- **Cache events**: Cache hits/misses (performance optimization)
- **Cleanup operations**: Automated file deletion tracking
- **Rate limiting**: Abuse detection and monitoring

Key requirements:
- **Separation of concerns**: Different log files for different purposes
- **Easy debugging**: Find relevant logs quickly
- **Production ready**: Rotate logs automatically (prevent disk fill)
- **Cost tracking**: Monitor Claude API usage and costs
- **Error alerting**: Quickly identify and investigate errors

## Decision

Implement a **dual-file logging strategy** with Flask's built-in `app.logger` as the single logging source, using Python's `RotatingFileHandler` for automatic log rotation.

### Log Files
1. **app.log**: General application logs (all levels including API calls)
2. **error.log**: Error-level logs only (quick error identification)

**Note**: The original design included `api.log` for separate API call tracking, but this was removed in v0.4.1 as it was never actually implemented and added unnecessary complexity. API calls are logged to `app.log` with structured formatting.

### Features
- **Rotating handlers**: 10MB max file size, 5 backup files (50MB total per log)
- **Structured formatting**: Timestamp, level, module, function, message
- **Console output**: Development mode logs to console
- **Configurable levels**: LOG_LEVEL environment variable
- **Single logger source**: All logging through Flask's `app.logger` or `current_app.logger`
- **Helper functions**: Structured logging helpers that internally use `current_app.logger`

### Implementation
```python
# logs/
#   app.log        - General application logs (including API calls)
#   app.log.1      - Rotated backup
#   error.log      - Errors only

# Setup logging
from logging.handlers import RotatingFileHandler

app_handler = RotatingFileHandler('logs/app.log', maxBytes=10MB, backupCount=5)
error_handler = RotatingFileHandler('logs/error.log', maxBytes=10MB, backupCount=5)

# All handlers attached to app.logger
app.logger.addHandler(app_handler)
app.logger.addHandler(error_handler)
```

## Alternatives Considered

### Alternative 1: Single Log File
- **Description**: All logs to one file (app.log)
- **Pros**:
  - Simplest implementation
  - Single file to check
  - Chronological order preserved
  - Easy to grep
- **Cons**:
  - Hard to find specific log types (errors, API calls)
  - Large file sizes (slower to search)
  - Cannot prioritize error monitoring
  - Mixed concerns (debugging and auditing)
  - Cost tracking requires parsing entire log
- **Rejected because**: Finding errors in a large mixed log file is time-consuming. Separate error.log allows quick error identification. API log separation enables cost tracking.

### Alternative 2: Centralized Logging Service (ELK, Datadog)
- **Description**: Send logs to external service (Elasticsearch, Datadog, Splunk)
- **Pros**:
  - Professional search and filtering
  - Dashboards and alerting
  - Distributed logging (multi-server)
  - Long-term retention
  - Advanced analytics
  - Real-time monitoring
- **Cons**:
  - Requires external service (cost: $50+/month)
  - Complex setup and configuration
  - Network dependency (logs may be lost)
  - Overkill for single-server app
  - Privacy concerns (logs leave server)
  - Vendor lock-in
- **Rejected because**: PDF Summarizer is a simple self-hosted app. External logging services add cost and complexity without benefits at this scale. File-based logging is sufficient.

### Alternative 3: Syslog
- **Description**: Send logs to system syslog daemon
- **Pros**:
  - Standard Unix logging mechanism
  - Centralized with other system logs
  - Built-in log rotation
  - Survives app crashes
  - rsyslog forwarding available
- **Cons**:
  - Platform-specific (different on Windows)
  - Mixed with system logs (harder to filter)
  - Less control over formatting
  - Requires syslog configuration
  - Not portable across OS
  - Debugging requires syslog knowledge
- **Rejected because**: Not portable across operating systems. Application-specific log files are easier to manage and debug. File-based logging works everywhere.

### Alternative 4: Database Logging
- **Description**: Store logs in SQLite database table
- **Pros**:
  - Queryable with SQL
  - Structured data (easy filtering)
  - Can JOIN with other tables
  - Retention policies easy to implement
  - Transaction support
- **Cons**:
  - Slower than file I/O
  - Database bloat (logs can be huge)
  - Harder to tail/watch logs
  - Database corruption risk
  - Difficult to export/archive
  - Performance impact on main database
- **Rejected because**: Logging should not impact database performance. Text files are simpler and faster. Databases are for application data, not logs.

### Alternative 5: JSON Structured Logging
- **Description**: Log in JSON format for machine parsing
- **Pros**:
  - Machine-readable
  - Easy to parse with tools (jq, logstash)
  - Structured data (fields, not text)
  - Better for log aggregators
- **Cons**:
  - Less human-readable
  - Harder to read in terminal
  - Overkill without aggregator
  - More verbose (larger files)
  - Not needed for simple app
- **Rejected because**: Human-readable logs are more important for debugging. JSON logs make sense with log aggregators (ELK), but not for file-based logging.

## Consequences

### Positive Consequences
- **Quick error identification**: Check error.log for problems (no noise)
- **Cost tracking**: app.log shows all Claude API calls with structured formatting
- **Performance debugging**: app.log shows request flow and timing
- **Automatic rotation**: Logs don't fill disk (50MB limit per log type)
- **Separation of concerns**: Errors separated for quick identification
- **Easy grep/tail**: Standard text files work with Unix tools
- **No external dependencies**: Built-in Python logging
- **Simple architecture**: Single logger source (`app.logger`) for entire application
- **Consistent patterns**: All helper functions use `current_app.logger` internally

### Negative Consequences
- **Multiple files to check**: Must look in 2 files for full picture
- **No cross-file correlation**: Timestamp matching required (though error.log duplicates app.log errors)
- **Disk space**: 100MB total (2 logs × 50MB) vs single file
- **More complex setup**: Two handlers instead of one

### Neutral Consequences
- **Manual monitoring**: No automated alerts (use external tools if needed)
- **Local storage only**: Logs stay on server (good for privacy)
- **Rotation by size**: Not time-based (10MB threshold)

## Implementation Notes

### Directory Structure
```
logs/
├── app.log           # Current general logs (includes API calls)
├── app.log.1         # Rotated backup (most recent)
├── app.log.2         # Older backup
├── ...
├── app.log.5         # Oldest backup
├── error.log         # Current error logs
└── error.log.1-5     # Error log backups
```

### Logging Configuration
```python
# src/pdf_summarizer/logging_config.py
from logging.handlers import RotatingFileHandler
from flask import current_app

def setup_logging(app):
    # App handler - all logs
    app_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5                # Keep 5 backups
    )
    app_handler.setFormatter(
        logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s (%(funcName)s): %(message)s')
    )

    # Error handler - errors only
    error_handler = RotatingFileHandler('logs/error.log', maxBytes=10MB, backupCount=5)
    error_handler.setLevel(logging.ERROR)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # All handlers attached to app.logger
    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)
```

### Logging Usage
```python
# Direct logging
from flask import current_app

current_app.logger.info("Upload successful")
current_app.logger.error("Failed to process PDF", exc_info=True)

# Using helper functions (recommended for structured logging)
from pdf_summarizer.logging_config import (
    log_upload, log_processing, log_api_call,
    log_cache_hit, log_cache_miss, log_cleanup
)

# Helper functions internally use current_app.logger - no logger parameter needed!
log_upload(filename, file_size, session_id)
log_processing(filename, pages, chars, duration)
log_api_call("Claude Summarization", duration, success=True)
log_cache_hit(file_hash)
log_cache_miss(file_hash)
log_cleanup(deleted_count, freed_space_mb)
```

### Code Locations
- Logging setup: [src/pdf_summarizer/logging_config.py](../../src/pdf_summarizer/logging_config.py)
- Helper functions: [src/pdf_summarizer/logging_config.py:81-132](../../src/pdf_summarizer/logging_config.py#L81-L132)
- Configuration: [src/pdf_summarizer/config.py:42-46](../../src/pdf_summarizer/config.py#L42-L46)

### Configuration
```python
# src/pdf_summarizer/config.py
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = os.getenv('LOG_DIR', 'logs')
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', str(10 * 1024 * 1024)))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
```

## Log Formats

### Detailed Format (app.log, error.log)
```
[2025-11-16 14:32:15,123] INFO in main (upload): Upload successful: document.pdf
[2025-11-16 14:32:16,456] ERROR in main (summarize_pdf): API call failed
Traceback (most recent call last):
  ...
```

### API Call Format (in app.log)
```
[2025-11-18 14:32:16] INFO in logging_config (log_api_call): API Call: Claude Summarization | Duration: 3.42s | Status: SUCCESS
[2025-11-18 14:32:20] INFO in logging_config (log_api_call): API Call: Claude Summarization | Duration: 2.18s | Status: SUCCESS
```

### Console Format (development)
```
[2025-11-16 14:32:15] INFO: Upload successful: document.pdf
[2025-11-16 14:32:16] ERROR: API call failed
```

## Log Levels

### Level Usage
```python
# DEBUG: Detailed diagnostic information (development only)
logger.debug(f"Processing page {page_num} of {total_pages}")

# INFO: General informational messages (default)
logger.info(f"Upload successful: {filename}")

# WARNING: Something unexpected but handled
logger.warning(f"Rate limit approaching: {count}/10")

# ERROR: Error that prevented operation
logger.error(f"Failed to process PDF: {error}", exc_info=True)

# CRITICAL: System-level failure (rare)
logger.critical(f"Database connection lost")
```

### Level Configuration
```bash
# Development
LOG_LEVEL=DEBUG

# Production
LOG_LEVEL=INFO

# Troubleshooting
LOG_LEVEL=WARNING
```

## Monitoring and Analysis

### Viewing Logs
```bash
# Tail application logs
tail -f logs/app.log

# Watch for errors
tail -f logs/error.log

# Monitor API calls (in app.log)
grep "API Call" logs/app.log | tail -f

# Search for specific event
grep "Cache HIT" logs/app.log
grep "FAILED" logs/app.log
```

### Cost Tracking
```bash
# Count API calls today
grep "$(date +%Y-%m-%d)" logs/app.log | grep "API Call" | wc -l

# Count successful API calls
grep "API Call" logs/app.log | grep SUCCESS | wc -l

# Calculate total API cost (estimate)
# Multiply count by ~$0.05 average cost per call
```

### Error Analysis
```bash
# Count errors by day
grep "ERROR" logs/error.log | cut -d' ' -f1 | uniq -c

# Find most common errors
grep "ERROR" logs/error.log | cut -d':' -f3 | sort | uniq -c | sort -rn
```

## Rotation and Retention

### Rotation Behavior
- **Size-based rotation**: When log reaches 10MB, rotate to .1
- **Backup count**: Keep 5 backups (oldest deleted automatically)
- **Total size**: 100MB total across both logs (60MB for app.log + 60MB for error.log, but error.log is typically much smaller)
- **Automatic**: No cron job or manual intervention needed

### Manual Rotation
```bash
# Force rotation (if needed)
rm logs/app.log.5  # Delete oldest
mv logs/app.log.4 logs/app.log.5
mv logs/app.log.3 logs/app.log.4
mv logs/app.log.2 logs/app.log.3
mv logs/app.log.1 logs/app.log.2
mv logs/app.log logs/app.log.1
touch logs/app.log
```

### Archival
```bash
# Archive old logs
tar -czf logs-archive-$(date +%Y%m%d).tar.gz logs/*.log.[1-5]
rm logs/*.log.[1-5]
```

## References

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [RotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler)
- [Flask Logging](https://flask.palletsprojects.com/en/3.0.x/logging/)
- [Logging Best Practices](https://docs.python-guide.org/writing/logging/)

## Updates and Revisions

### Version 0.4.1 (2025-11-18): Logging Harmonization

**Changes Made**:
- **Removed `api.log` file**: Originally planned but never implemented; added unnecessary complexity
- **Simplified to dual-file strategy**: Only `app.log` (all logs) and `error.log` (errors only)
- **Removed logger parameters**: All helper functions now use `current_app.logger` internally
  - `log_upload(filename, size, session)` - no logger param
  - `log_processing(filename, pages, chars, duration)` - no logger param
  - `log_api_call(operation, duration, success, error)` - no logger param
  - `log_cache_hit(file_hash)` - no logger param
  - `log_cache_miss(file_hash)` - no logger param
  - `log_cleanup(deleted_count, freed_space_mb)` - no logger param
  - `log_error_with_context(error, context)` - no logger param
- **Single logger source**: All code uses `app.logger` or `current_app.logger` exclusively
- **Consistent architecture**: No named loggers, no logger passing, single pattern throughout

**Rationale**:
- Simpler API: Functions don't need logger passed as argument
- Less complexity: Two log files instead of three
- Consistent: Single pattern used everywhere in codebase
- Easier to maintain: One logger source to manage
- Cleaner code: Helper functions are simpler to use

## Related ADRs

- Related to: ADR-0004 (Use Anthropic Claude API) - API call logging
- Related to: ADR-0006 (SHA256 Hash-Based Caching) - Cache event logging
- Related to: ADR-0009 (Use APScheduler for Background Jobs) - Cleanup logging
