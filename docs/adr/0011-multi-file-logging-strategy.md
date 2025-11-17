# ADR-0011: Multi-File Logging Strategy

**Status**: Accepted

**Date**: 2025-11-16

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

Implement a **multi-file logging strategy** with separate log files for different concerns, using Python's `RotatingFileHandler` for automatic log rotation.

### Log Files
1. **app.log**: General application logs (all levels)
2. **error.log**: Error-level logs only (quick error identification)
3. **api.log**: External API calls to Claude (cost tracking)

### Features
- **Rotating handlers**: 10MB max file size, 5 backup files (50MB total per log)
- **Structured formatting**: Timestamp, level, module, function, message
- **Console output**: Development mode logs to console
- **Configurable levels**: LOG_LEVEL environment variable
- **Named loggers**: Separate logger for API calls (`logging.getLogger("api")`)

### Implementation
```python
# logs/
#   app.log        - General application logs
#   app.log.1      - Rotated backup
#   error.log      - Errors only
#   api.log        - Claude API calls

# Setup logging
from logging.handlers import RotatingFileHandler

app_handler = RotatingFileHandler('logs/app.log', maxBytes=10MB, backupCount=5)
error_handler = RotatingFileHandler('logs/error.log', maxBytes=10MB, backupCount=5)
api_handler = RotatingFileHandler('logs/api.log', maxBytes=10MB, backupCount=5)
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
- **Cost tracking**: api.log shows all Claude API calls with latency
- **Performance debugging**: app.log shows request flow and timing
- **Automatic rotation**: Logs don't fill disk (50MB limit per log type)
- **Separation of concerns**: Different logs for different purposes
- **Easy grep/tail**: Standard text files work with Unix tools
- **No external dependencies**: Built-in Python logging

### Negative Consequences
- **Multiple files to check**: Must look in 2-3 files for full picture
- **No cross-file correlation**: Timestamp matching required
- **Disk space**: 150MB total (3 logs × 50MB) vs single file
- **More complex setup**: Three handlers instead of one
- **Log aggregation**: Harder to view chronological order across files

### Neutral Consequences
- **Manual monitoring**: No automated alerts (use external tools if needed)
- **Local storage only**: Logs stay on server (good for privacy)
- **Rotation by size**: Not time-based (10MB threshold)

## Implementation Notes

### Directory Structure
```
logs/
├── app.log           # Current general logs
├── app.log.1         # Rotated backup (most recent)
├── app.log.2         # Older backup
├── ...
├── app.log.5         # Oldest backup
├── error.log         # Current error logs
├── error.log.1-5     # Error log backups
├── api.log           # Current API logs
└── api.log.1-5       # API log backups
```

### Logging Configuration
```python
# src/pdf_summarizer/logging_config.py
from logging.handlers import RotatingFileHandler

def setup_logging(app):
    # App handler - all logs
    app_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5                # Keep 5 backups
    )
    app_handler.setFormatter(
        logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    )

    # Error handler - errors only
    error_handler = RotatingFileHandler('logs/error.log', maxBytes=10MB, backupCount=5)
    error_handler.setLevel(logging.ERROR)

    # API handler - external API calls
    api_logger = logging.getLogger('api')
    api_handler = RotatingFileHandler('logs/api.log', maxBytes=10MB, backupCount=5)
    api_logger.addHandler(api_handler)
    api_logger.propagate = False  # Don't duplicate in app.log
```

### Logging Usage
```python
# General application log
app.logger.info("Upload successful")
app.logger.error("Failed to process PDF", exc_info=True)

# API call log
api_logger = logging.getLogger('api')
api_logger.info(f"Claude API call: {duration:.2f}s | {input_tokens} tokens | ${cost:.4f}")

# Cache events
app.logger.info(f"Cache HIT: {file_hash[:16]}...")
app.logger.info(f"Cache MISS: {file_hash[:16]}...")

# Cleanup
app.logger.info(f"Cleanup: deleted {count} files, freed {size_mb:.2f}MB")
```

### Code Locations
- Logging setup: [src/pdf_summarizer/logging_config.py](../../src/pdf_summarizer/logging_config.py)
- Helper functions: [src/pdf_summarizer/logging_config.py:92-140](../../src/pdf_summarizer/logging_config.py#L92-L140)
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

### Simple Format (api.log)
```
[2025-11-16 14:32:16,789] INFO: API Call: summarize | Duration: 3.42s | Status: SUCCESS
[2025-11-16 14:32:20,123] INFO: API Call: summarize | Duration: 2.18s | Status: SUCCESS
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

# Monitor API calls
tail -f logs/api.log

# Search for specific event
grep "Cache HIT" logs/app.log
grep "FAILED" logs/api.log
```

### Cost Tracking
```bash
# Count API calls today
grep "$(date +%Y-%m-%d)" logs/api.log | wc -l

# Calculate total API cost (estimate)
grep "API Call" logs/api.log | grep SUCCESS | wc -l
# Multiply by ~$0.05 average cost per call
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
- **Total size**: 60MB per log type (10MB current + 5×10MB backups)
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

## Related ADRs

- Related to: ADR-0004 (Use Anthropic Claude API) - API call logging
- Related to: ADR-0006 (SHA256 Hash-Based Caching) - Cache event logging
- Related to: ADR-0009 (Use APScheduler for Background Jobs) - Cleanup logging
