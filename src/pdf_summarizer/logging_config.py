# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Logging configuration for PDF Summarizer application
Provides structured logging with rotating file handlers
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import current_app

from .config import Config


def setup_logging(app):
    """
    Configure logging for the Flask application

    Creates separate log files for:
    - app.log: General application logs
    - error.log: Error-level logs only
    - api.log: External API calls (Claude)

    Args:
        app: Flask application instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(Config.LOG_DIR)
    log_dir.mkdir(exist_ok=True)

    # Get log level from configuration
    log_level = Config.LOG_LEVEL.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s (%(funcName)s): %(message)s"
    )

    simple_formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")

    # Main application log handler
    app_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=Config.LOG_MAX_BYTES, backupCount=Config.LOG_BACKUP_COUNT
    )
    app_handler.setLevel(numeric_level)
    app_handler.setFormatter(detailed_formatter)

    # Error log handler (errors only)
    error_handler = RotatingFileHandler(
        log_dir / "error.log", maxBytes=Config.LOG_MAX_BYTES, backupCount=Config.LOG_BACKUP_COUNT
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Configure app logger
    app.logger.setLevel(numeric_level)
    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(console_handler)

    # Log startup
    app.logger.info("PDF Summarizer Application Started")
    app.logger.info(f"Log Level: {log_level}")
    app.logger.info(f"Debug Mode: {app.debug}")


def log_upload(filename, file_size, session_id):
    """Log file upload event"""
    current_app.logger.info(
        f"Upload: {filename} | Size: {file_size} bytes | Session: {session_id[:8]}..."
    )


def log_processing(filename, pages, chars, duration):
    """Log PDF processing completion"""
    current_app.logger.info(
        f"Processed: {filename} | Pages: {pages} | Chars: {chars:,} | Duration: {duration:.2f}s"
    )


def log_api_call(operation, duration, success=True, error=None):
    """Log external API calls"""
    status = "SUCCESS" if success else "FAILED"
    msg = f"API Call: {operation} | Duration: {duration:.2f}s | Status: {status}"
    if error:
        msg += f" | Error: {error}"
        current_app.logger.error(msg)
    else:
        current_app.logger.info(msg)


def log_cache_hit(file_hash):
    """Log cache hit event"""
    current_app.logger.info(f"Cache HIT: {file_hash[:16]}... (returning cached summary)")


def log_cache_miss(file_hash):
    """Log cache miss event"""
    current_app.logger.info(f"Cache MISS: {file_hash[:16]}... (processing new file)")


def log_rate_limit(identifier, endpoint):
    """Log rate limit event"""
    current_app.logger.warning(f"Rate limit exceeded: {identifier} on {endpoint}")


def log_cleanup(deleted_count, freed_space_mb):
    """Log cleanup operation"""
    current_app.logger.info(
        f"Cleanup completed: {deleted_count} files deleted | {freed_space_mb:.2f} MB freed"
    )


def log_error_with_context(error, context):
    """Log error with additional context"""
    current_app.logger.error(f"Error: {str(error)} | Context: {context}", exc_info=True)
