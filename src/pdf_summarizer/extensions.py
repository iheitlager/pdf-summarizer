# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Flask extensions module.

This module provides singleton extension instances that are initialized
by the application factory. This pattern ensures extensions are properly
configured and can be safely imported throughout the application.
"""

from anthropic import Anthropic
from apscheduler.schedulers.background import BackgroundScheduler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Database extension
db = SQLAlchemy()

# Database migration extension
migrate = Migrate()

# Rate limiting extension
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
)


class AnthropicExtension:
    """
    Flask extension wrapper for Anthropic API client.

    This extension manages the Anthropic client lifecycle and ensures
    it's properly initialized with the API key from app configuration.
    """

    def __init__(self, app=None):
        """Initialize extension, optionally with an app instance."""
        self.client = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize the extension with a Flask app.

        Args:
            app: Flask application instance
        """
        api_key = app.config.get("ANTHROPIC_API_KEY")
        if api_key:
            self.client = Anthropic(api_key=api_key)
            app.logger.info("Anthropic client initialized")
        else:
            app.logger.warning("ANTHROPIC_API_KEY not set - Claude features will not work")

        # Register extension in app
        if not hasattr(app, "extensions"):
            app.extensions = {}
        app.extensions["anthropic"] = self


class CleanupScheduler:
    """
    Flask extension wrapper for background cleanup scheduler.

    This extension manages the APScheduler instance that runs periodic
    cleanup jobs. It can be started/stopped and properly integrates with
    Flask's application context.
    """

    def __init__(self, app=None):
        """Initialize extension, optionally with an app instance."""
        self.scheduler = None
        self.app = None
        if app:
            self.init_app(app)

    def init_app(self, app, start=True):
        """
        Initialize the extension with a Flask app.

        Args:
            app: Flask application instance
            start: Whether to start the scheduler immediately (default: True)
        """
        self.app = app

        if start:
            from .cleanup import cleanup_old_uploads

            self.scheduler = BackgroundScheduler()

            # Get cleanup schedule from config
            cleanup_hour = app.config.get("CLEANUP_HOUR", 3)
            cleanup_minute = app.config.get("CLEANUP_MINUTE", 0)

            # Add cleanup job
            self.scheduler.add_job(
                func=lambda: cleanup_old_uploads(app),
                trigger="cron",
                hour=cleanup_hour,
                minute=cleanup_minute,
            )

            self.scheduler.start()
            app.logger.info(
                f"Cleanup scheduler started (runs daily at {cleanup_hour:02d}:{cleanup_minute:02d})"
            )
        else:
            app.logger.info("Cleanup scheduler disabled (start=False)")

        # Register extension in app
        if not hasattr(app, "extensions"):
            app.extensions = {}
        app.extensions["cleanup_scheduler"] = self

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            if self.app:
                self.app.logger.info("Cleanup scheduler shutdown")


# Create singleton instances
anthropic_ext = AnthropicExtension()
cleanup_scheduler = CleanupScheduler()
