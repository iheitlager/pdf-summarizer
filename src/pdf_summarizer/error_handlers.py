# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Error handlers module.

This module provides custom error handlers for common HTTP errors,
rendering user-friendly error pages.
"""

from flask import render_template, request
from flask_limiter.util import get_remote_address

from .extensions import db
from .logging_config import log_rate_limit


def register_error_handlers(app):
    """
    Register error handlers with the Flask application.

    Args:
        app: Flask application instance
    """

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        app.logger.warning(f"404 error: {request.url}")
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        db.session.rollback()
        app.logger.error(f"500 error: {str(error)}", exc_info=True)
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handle 429 Rate Limit Exceeded errors."""
        log_rate_limit(app.logger, get_remote_address(), request.endpoint)
        return render_template("errors/429.html"), 429
