# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Main entry point for PDF Summarizer application.

This module provides the CLI entry point for running the application.
It uses the application factory pattern to create and configure the
Flask application instance.
"""

import sys

from .config import Config
from .factory import create_app

# For backward compatibility with tests that import from main module
# These will be initialized when create_app() is called
app = None
api_logger = None
db = None
limiter = None
anthropic_client = None
scheduler = None

# Import models for backward compatibility
from .models import Summary, Upload  # noqa: E402, F401


def _initialize_module_globals():
    """
    Initialize module-level globals for backward compatibility.

    This function exists to support existing tests that import directly
    from the main module. New code should use the factory pattern instead.
    """
    global app, api_logger, db, limiter, anthropic_client, scheduler

    # Create application using factory
    app = create_app(
        start_scheduler=not any("pytest" in arg or "conftest" in arg for arg in sys.argv)
    )

    # Set module-level globals for backward compatibility
    from .extensions import cleanup_scheduler
    from .extensions import db as db_ext
    from .extensions import limiter as limiter_ext

    db = db_ext
    limiter = limiter_ext
    scheduler = cleanup_scheduler.scheduler
    api_logger = app.logger  # Use app.logger for api_logger

    # Get Anthropic client from extension
    if hasattr(app, "extensions") and "anthropic" in app.extensions:
        anthropic_client = app.extensions["anthropic"].client

    return app, api_logger


# Only initialize globals if not running in pytest
# Tests should use the factory pattern directly
if not any("pytest" in arg or "conftest" in arg for arg in sys.argv):
    # Load CLI configuration before creating app
    try:
        Config.from_cli_args()
    except SystemExit:
        # Silently handle argparse system exit during import
        pass

    # Initialize module globals for direct execution
    if __name__ == "__main__":
        app, api_logger = _initialize_module_globals()


if __name__ == "__main__":
    # Validate configuration
    errors = Config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    # Run the application
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
