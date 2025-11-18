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
from .models import PromptTemplate
from .routes import register_routes


def init_default_prompt(app):
    """
    Initialize the default prompt template if none exists.

    Creates a "Basic Summary" prompt template on first run to ensure
    the application has at least one prompt available.

    Args:
        app: Flask application instance
    """
    if PromptTemplate.query.count() == 0:
        default_prompt = PromptTemplate(
            name=app.config.get("DEFAULT_PROMPT_NAME", "Basic Summary"),
            prompt_text=app.config.get(
                "DEFAULT_PROMPT_TEXT",
                "Please provide a concise summary of the following document. "
                "Focus on the main points, key findings, and important details:",
            ),
            is_active=True,
        )
        db.session.add(default_prompt)
        db.session.commit()
        app.logger.info(f"Created default prompt template: {default_prompt.name}")
    else:
        app.logger.debug(f"Found {PromptTemplate.query.count()} existing prompt templates")


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

    # If test or runtime callers provide overrides, apply them to the Config
    # class before validation so validation uses the effective values.
    if config_overrides:
        for key, value in config_overrides.items():
            # Only set uppercase config attributes to avoid clobbering
            # internal or unrelated keys.
            if isinstance(key, str) and key.isupper():
                setattr(Config, key, value)

    # Validate configuration after applying overrides
    errors = Config.validate()
    if errors:
        raise ValueError("Configuration validation failed", errors)

    # Create Flask application
    app = Flask(__name__)

    # Load base configuration from Config class
    app.config.from_object(Config)

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

        # Initialize default prompt template
        init_default_prompt(app)

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
