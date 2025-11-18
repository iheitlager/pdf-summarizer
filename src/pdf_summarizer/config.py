# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Configuration module for PDF Summarizer application.

Loads configuration from environment variables with sensible defaults.
Supports command-line argument overrides.
"""

import argparse
import os
from datetime import timedelta
from pathlib import Path


class Config:
    """Application configuration class."""

    # Flask Configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///pdf_summaries.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv("SESSION_LIFETIME_DAYS", "30")))

    # Upload Configuration
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

    # Anthropic API Configuration
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    SKIP_CLAUDE_VALIDATION = os.getenv("SKIP_CLAUDE_VALIDATION", "false").lower()[0] in [
        "1",
        "y",
        "t",
    ]
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))
    MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "100000"))

    # Prompt Template Configuration
    DEFAULT_PROMPT_NAME = "Basic Summary"
    DEFAULT_PROMPT_TEXT = (
        "Please provide a concise summary of the following document. "
        "Focus on the main points, key findings, and important details:"
    )

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")
    RATE_LIMIT_UPLOAD = os.getenv("RATE_LIMIT_UPLOAD", "10 per hour")
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "200 per day")

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # Cleanup Configuration
    RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))
    CLEANUP_HOUR = int(os.getenv("CLEANUP_HOUR", "3"))
    CLEANUP_MINUTE = int(os.getenv("CLEANUP_MINUTE", "0"))

    # Flask Server Configuration
    # Default to 0.0.0.0 in Docker containers, 127.0.0.1 otherwise
    # Check for common container indicators
    _in_container = os.path.exists("/.dockerenv") or os.getenv("KUBERNETES_SERVICE_HOST")
    HOST = os.getenv("FLASK_HOST", "0.0.0.0" if _in_container else "127.0.0.1")
    PORT = int(os.getenv("FLASK_PORT", "8000"))
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    FLASK_ENV = os.getenv("FLASK_ENV", "production")

    @classmethod
    def from_cli_args(cls, args=None):
        """
        Update configuration from command-line arguments.

        Args:
            args: Parsed argparse Namespace object or None to parse from sys.argv
        """
        if args is None:
            parser = cls.create_argument_parser()
            # Use parse_known_args so test runners (pytest) or other wrappers
            # passing extra args don't cause argparse to exit the process.
            args, _ = parser.parse_known_args()

        # Override configuration from CLI args
        if args.host:
            cls.HOST = args.host
        if args.port:
            cls.PORT = args.port
        if args.debug:
            cls.DEBUG = True
            cls.FLASK_ENV = "development"
        if args.api_key:
            cls.ANTHROPIC_API_KEY = args.api_key
        if args.database:
            cls.SQLALCHEMY_DATABASE_URI = args.database
        if args.upload_folder:
            cls.UPLOAD_FOLDER = args.upload_folder
        if args.log_level:
            cls.LOG_LEVEL = args.log_level.upper()
        if args.retention_days is not None:
            cls.RETENTION_DAYS = args.retention_days

    @staticmethod
    def create_argument_parser():
        """Create and return argument parser for CLI options."""
        parser = argparse.ArgumentParser(
            description="PDF Summarizer - AI-powered PDF summarization service",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        # Server options
        server_group = parser.add_argument_group("Server Options")
        server_group.add_argument(
            "--host", type=str, help="Host to bind the server to (default: 127.0.0.1)"
        )
        server_group.add_argument(
            "--port", "-p", type=int, help="Port to bind the server to (default: 8000)"
        )
        server_group.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")

        # API options
        api_group = parser.add_argument_group("API Options")
        api_group.add_argument(
            "--api-key", type=str, help="Anthropic API key (overrides ANTHROPIC_API_KEY env var)"
        )

        # Storage options
        storage_group = parser.add_argument_group("Storage Options")
        storage_group.add_argument(
            "--database", type=str, help="Database URI (default: sqlite:///pdf_summaries.db)"
        )
        storage_group.add_argument(
            "--upload-folder", type=str, help="Folder for uploaded PDFs (default: uploads)"
        )

        # Logging options
        logging_group = parser.add_argument_group("Logging Options")
        logging_group.add_argument(
            "--log-level",
            type=str,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Logging level",
        )

        # Cleanup options
        cleanup_group = parser.add_argument_group("Cleanup Options")
        cleanup_group.add_argument(
            "--retention-days",
            type=int,
            help="Number of days to retain uploads (default: 30)",
        )

        return parser

    @classmethod
    def validate(cls):
        """Validate required configuration values."""
        errors = []

        # Require Anthropic API key by default. Tests that need to skip
        # this check should set `SKIP_CLAUDE_VALIDATION` on the Config
        # class (or pass it via `create_app(..., config_overrides=...)`).
        if not cls.ANTHROPIC_API_KEY:
            errors.append(
                "ANTHROPIC_API_KEY is required. Set it via environment variable or --api-key flag."
            )

        if not cls.SECRET_KEY or cls.SECRET_KEY == "dev-secret-key-change-in-production":
            if cls.FLASK_ENV == "production":
                errors.append(
                    "SECRET_KEY must be set to a secure random value in production. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
                )

        return errors

    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        Path(cls.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(cls.LOG_DIR).mkdir(parents=True, exist_ok=True)

    @classmethod
    def to_dict(cls):
        """Return configuration as dictionary (for Flask app.config.from_object)."""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_") and key.isupper()
        }
