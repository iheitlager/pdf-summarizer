# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Application factory module.

This module provides the create_app() factory function that creates
and configures Flask application instances. This pattern enables:
- Testing with different configurations
- Multiple app instances in the same process
- Deferred extension initialization
- Proper separation of concerns
"""


from flask import Flask

from .claude_service import validate_claude_model
from .config import Config
from .error_handlers import register_error_handlers
from .extensions import anthropic_ext, cleanup_scheduler, db, limiter, migrate
from .logging_config import setup_logging
from .routes import register_routes


def create_app(config_overrides=None, start_scheduler=True):
    """
    Create and configure a Flask application instance.

    This is the application factory function that initializes all
    extensions, registers routes and error handlers, and sets up
    the application configuration.

    Args:
        config_overrides: Dictionary of configuration values to override
                         defaults (useful for testing)
        start_scheduler: Whether to start the background cleanup scheduler
                        (default: True, set to False in tests)

    Returns:
        Flask: Flask app instance

    Example:
        # Production use
        app = create_app()

        # Testing use
        app = create_app(
            config_overrides={'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'},
            start_scheduler=False
        )
    """
    from dotenv import load_dotenv
    
    # Load environment variables if not already loaded
    load_dotenv()
    # Validate configuration
    Config.from_cli_args()
    errors = Config.validate()
    if errors:
        raise ValueError("Configuration validation failed", errors)


    # Create Flask application
    app = Flask(__name__)

    # Load base configuration from Config class
    app.config.from_object(Config)

    # Apply configuration overrides (from tests or other sources)
    if config_overrides:
        app.config.update(config_overrides)

    # Ensure required directories exist
    Config.ensure_directories()

    # Initialize database extension
    db.init_app(app)

    # Initialize migration extension
    migrate.init_app(app, db)

    limiter.init_app(app)

    # Initialize Anthropic extension
    anthropic_ext.init_app(app)

    # Initialize cleanup scheduler
    cleanup_scheduler.init_app(app, start=start_scheduler)

    # Setup logging
    setup_logging(app)

    # Register error handlers
    register_error_handlers(app)

    # Register routes
    register_routes(app)

    # Create database tables and validate Claude model
    with app.app_context():
        db.create_all()

        if not app.config.get("SKIP_CLAUDE_VALIDATION", False):
            if not validate_claude_model(app):
                raise RuntimeError(
                    "Claude model is not available. Check CLAUDE_MODEL environment variable and API key"
                )

    # Register teardown handler to shutdown scheduler
    @app.teardown_appcontext
    def shutdown_extensions(exception=None):
        """Shutdown extensions when app context ends."""
        cleanup_scheduler.shutdown()

    app.logger.info("Application factory initialized successfully")
    return app
