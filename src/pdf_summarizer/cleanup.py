# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Cleanup service module.

This module provides background cleanup functionality for removing
old PDF uploads and their associated database records.
"""

import os
from datetime import UTC, datetime, timedelta

from .extensions import db
from .logging_config import log_cleanup, log_error_with_context
from .models import Upload


def cleanup_old_uploads(app):
    """
    Delete uploads older than retention period.

    This function is called by the background scheduler to periodically
    clean up old uploads and free disk space.

    Args:
        app: Flask application instance (needed for config and context)
    """
    with app.app_context():
        try:
            # Read RETENTION_DAYS from environment for test compatibility
            retention_days = int(os.getenv("RETENTION_DAYS", app.config.get("RETENTION_DAYS", 30)))
            cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

            old_uploads = Upload.query.filter(Upload.upload_date < cutoff_date).all()

            deleted_count = 0
            freed_space = 0

            for upload in old_uploads:
                # Delete file from disk
                if os.path.exists(upload.file_path):
                    file_size = os.path.getsize(upload.file_path)
                    os.remove(upload.file_path)
                    freed_space += file_size
                    app.logger.info(f"Deleted file: {upload.file_path}")

                # Delete from database (cascades to summaries)
                db.session.delete(upload)
                deleted_count += 1

            db.session.commit()

            freed_space_mb = freed_space / (1024 * 1024)
            log_cleanup(app.logger, deleted_count, freed_space_mb)
            app.logger.info(
                f"Cleanup completed: {deleted_count} files, {freed_space_mb:.2f} MB freed"
            )

        except Exception as e:
            db.session.rollback()
            log_error_with_context(app.logger, e, "Cleanup job")
