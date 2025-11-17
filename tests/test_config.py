# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Tests for configuration module.

Tests cover:
- Environment variable reading with defaults
- CLI argument parsing and overrides
- Configuration validation
- Directory creation
- Configuration dictionary conversion
"""

import argparse
import os
from pathlib import Path
from unittest.mock import patch

from pdf_summarizer.config import Config


class TestConfigDefaults:
    """Tests for default configuration values."""

    def test_default_flask_config(self):
        """Should have correct Flask defaults."""
        assert Config.SECRET_KEY == "dev-secret-key-change-in-production"
        assert Config.SQLALCHEMY_DATABASE_URI == "sqlite:///pdf_summaries.db"
        assert Config.SQLALCHEMY_TRACK_MODIFICATIONS is False
        assert Config.MAX_CONTENT_LENGTH == 10 * 1024 * 1024  # 10MB

    def test_default_upload_folder(self):
        """Should have correct upload folder default."""
        assert Config.UPLOAD_FOLDER == "uploads"

    def test_default_anthropic_config(self):
        """Should have correct Anthropic API defaults."""
        assert Config.CLAUDE_MODEL == "claude-sonnet-4-5-20250929"
        assert Config.MAX_TOKENS == 1024
        assert Config.MAX_TEXT_LENGTH == 100000

    def test_default_rate_limiting_config(self):
        """Should have correct rate limiting defaults."""
        assert Config.RATE_LIMIT_ENABLED is True
        assert Config.RATE_LIMIT_STORAGE_URI == "memory://"
        assert Config.RATE_LIMIT_UPLOAD == "10 per hour"
        assert Config.RATE_LIMIT_DEFAULT == "200 per day"

    def test_default_logging_config(self):
        """Should have correct logging defaults."""
        assert Config.LOG_LEVEL == "INFO"
        assert Config.LOG_DIR == "logs"
        assert Config.LOG_MAX_BYTES == 10 * 1024 * 1024  # 10MB
        assert Config.LOG_BACKUP_COUNT == 5

    def test_default_cleanup_config(self):
        """Should have correct cleanup defaults."""
        assert Config.RETENTION_DAYS == 30
        assert Config.CLEANUP_HOUR == 3
        assert Config.CLEANUP_MINUTE == 0

    def test_default_server_config(self):
        """Should have correct server defaults."""
        assert Config.HOST == "127.0.0.1"
        assert Config.PORT == 5000
        assert Config.DEBUG is False
        assert Config.FLASK_ENV == "production"


class TestConfigEnvironmentVariables:
    """Tests for reading configuration from environment variables."""

    def test_reads_secret_key_from_env(self):
        """Should read SECRET_KEY from environment."""
        with patch.dict(os.environ, {"SECRET_KEY": "custom-secret-key"}):
            # Need to reload the class to pick up new env var
            from importlib import reload

            from pdf_summarizer import config

            reload(config)
            assert config.Config.SECRET_KEY == "custom-secret-key"

    def test_reads_database_url_from_env(self):
        """Should read DATABASE_URL from environment."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/testdb"}):
            from importlib import reload

            from pdf_summarizer import config

            reload(config)
            assert config.Config.SQLALCHEMY_DATABASE_URI == "postgresql://localhost/testdb"

    def test_reads_max_file_size_from_env(self):
        """Should read and convert MAX_FILE_SIZE_MB from environment."""
        with patch.dict(os.environ, {"MAX_FILE_SIZE_MB": "20"}):
            from importlib import reload

            from pdf_summarizer import config

            reload(config)
            assert config.Config.MAX_CONTENT_LENGTH == 20 * 1024 * 1024

    def test_reads_anthropic_api_key_from_env(self):
        """Should read ANTHROPIC_API_KEY from environment."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key-123"}):
            from importlib import reload

            from pdf_summarizer import config

            reload(config)
            assert config.Config.ANTHROPIC_API_KEY == "test-api-key-123"

    def test_reads_claude_model_from_env(self):
        """Should read CLAUDE_MODEL from environment."""
        with patch.dict(os.environ, {"CLAUDE_MODEL": "claude-3-opus-20240229"}):
            from importlib import reload

            from pdf_summarizer import config

            reload(config)
            assert config.Config.CLAUDE_MODEL == "claude-3-opus-20240229"

    def test_reads_log_level_from_env(self):
        """Should read LOG_LEVEL from environment."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            from importlib import reload

            from pdf_summarizer import config

            reload(config)
            assert config.Config.LOG_LEVEL == "DEBUG"

    def test_reads_retention_days_from_env(self):
        """Should read and convert RETENTION_DAYS from environment."""
        with patch.dict(os.environ, {"RETENTION_DAYS": "60"}):
            from importlib import reload

            from pdf_summarizer import config

            reload(config)
            assert config.Config.RETENTION_DAYS == 60


class TestConfigCLIArguments:
    """Tests for CLI argument parsing and overrides."""

    def test_cli_override_host(self):
        """Should override host from CLI argument."""
        args = argparse.Namespace(
            host="0.0.0.0",
            port=None,
            debug=False,
            api_key=None,
            database=None,
            upload_folder=None,
            log_level=None,
            retention_days=None,
        )
        Config.from_cli_args(args)
        assert Config.HOST == "0.0.0.0"

    def test_cli_override_port(self):
        """Should override port from CLI argument."""
        args = argparse.Namespace(
            host=None,
            port=8080,
            debug=False,
            api_key=None,
            database=None,
            upload_folder=None,
            log_level=None,
            retention_days=None,
        )
        Config.from_cli_args(args)
        assert Config.PORT == 8080

    def test_cli_override_debug(self):
        """Should enable debug mode from CLI argument."""
        args = argparse.Namespace(
            host=None,
            port=None,
            debug=True,
            api_key=None,
            database=None,
            upload_folder=None,
            log_level=None,
            retention_days=None,
        )
        Config.from_cli_args(args)
        assert Config.DEBUG is True
        assert Config.FLASK_ENV == "development"

    def test_cli_override_api_key(self):
        """Should override API key from CLI argument."""
        args = argparse.Namespace(
            host=None,
            port=None,
            debug=False,
            api_key="cli-api-key-456",
            database=None,
            upload_folder=None,
            log_level=None,
            retention_days=None,
        )
        Config.from_cli_args(args)
        assert Config.ANTHROPIC_API_KEY == "cli-api-key-456"

    def test_cli_override_database(self):
        """Should override database URI from CLI argument."""
        args = argparse.Namespace(
            host=None,
            port=None,
            debug=False,
            api_key=None,
            database="sqlite:///custom.db",
            upload_folder=None,
            log_level=None,
            retention_days=None,
        )
        Config.from_cli_args(args)
        assert Config.SQLALCHEMY_DATABASE_URI == "sqlite:///custom.db"

    def test_cli_override_upload_folder(self):
        """Should override upload folder from CLI argument."""
        args = argparse.Namespace(
            host=None,
            port=None,
            debug=False,
            api_key=None,
            database=None,
            upload_folder="/tmp/custom/uploads",
            log_level=None,
            retention_days=None,
        )
        Config.from_cli_args(args)
        assert Config.UPLOAD_FOLDER == "/tmp/custom/uploads"

    def test_cli_override_log_level(self):
        """Should override log level from CLI argument."""
        args = argparse.Namespace(
            host=None,
            port=None,
            debug=False,
            api_key=None,
            database=None,
            upload_folder=None,
            log_level="warning",
            retention_days=None,
        )
        Config.from_cli_args(args)
        assert Config.LOG_LEVEL == "WARNING"

    def test_cli_override_retention_days(self):
        """Should override retention days from CLI argument."""
        args = argparse.Namespace(
            host=None,
            port=None,
            debug=False,
            api_key=None,
            database=None,
            upload_folder=None,
            log_level=None,
            retention_days=90,
        )
        Config.from_cli_args(args)
        assert Config.RETENTION_DAYS == 90

    def test_cli_override_multiple_args(self):
        """Should handle multiple CLI argument overrides."""
        args = argparse.Namespace(
            host="0.0.0.0",
            port=8080,
            debug=True,
            api_key="multi-test-key",
            database="postgresql://localhost/db",
            upload_folder="/tmp/uploads",
            log_level="debug",
            retention_days=45,
        )
        Config.from_cli_args(args)
        assert Config.HOST == "0.0.0.0"
        assert Config.PORT == 8080
        assert Config.DEBUG is True
        assert Config.ANTHROPIC_API_KEY == "multi-test-key"
        assert Config.SQLALCHEMY_DATABASE_URI == "postgresql://localhost/db"
        assert Config.UPLOAD_FOLDER == "/tmp/uploads"
        assert Config.LOG_LEVEL == "DEBUG"
        assert Config.RETENTION_DAYS == 45


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_validation_fails_without_api_key(self):
        """Should fail validation when ANTHROPIC_API_KEY is missing."""
        original_key = Config.ANTHROPIC_API_KEY
        Config.ANTHROPIC_API_KEY = None

        errors = Config.validate()
        assert len(errors) > 0
        assert any("ANTHROPIC_API_KEY" in error for error in errors)

        # Restore
        Config.ANTHROPIC_API_KEY = original_key

    def test_validation_fails_with_default_secret_in_production(self):
        """Should fail validation with default SECRET_KEY in production."""
        original_key = Config.SECRET_KEY
        original_env = Config.FLASK_ENV

        Config.SECRET_KEY = "dev-secret-key-change-in-production"
        Config.FLASK_ENV = "production"

        errors = Config.validate()
        assert len(errors) > 0
        assert any("SECRET_KEY" in error for error in errors)

        # Restore
        Config.SECRET_KEY = original_key
        Config.FLASK_ENV = original_env

    def test_validation_succeeds_with_default_secret_in_development(self):
        """Should pass validation with default SECRET_KEY in development."""
        original_key = Config.SECRET_KEY
        original_env = Config.FLASK_ENV

        Config.SECRET_KEY = "dev-secret-key-change-in-production"
        Config.FLASK_ENV = "development"

        errors = Config.validate()
        # Should not have SECRET_KEY error in development
        assert not any("SECRET_KEY" in error for error in errors)

        # Restore
        Config.SECRET_KEY = original_key
        Config.FLASK_ENV = original_env

    def test_validation_succeeds_with_valid_config(self):
        """Should pass validation with valid configuration."""
        original_key = Config.ANTHROPIC_API_KEY
        original_secret = Config.SECRET_KEY

        Config.ANTHROPIC_API_KEY = "valid-api-key"
        Config.SECRET_KEY = "secure-secret-key-12345"

        errors = Config.validate()
        assert len(errors) == 0

        # Restore
        Config.ANTHROPIC_API_KEY = original_key
        Config.SECRET_KEY = original_secret


class TestConfigHelpers:
    """Tests for configuration helper methods."""

    def test_ensure_directories_creates_upload_folder(self, tmp_path):
        """Should create upload folder if it doesn't exist."""
        original_folder = Config.UPLOAD_FOLDER
        Config.UPLOAD_FOLDER = str(tmp_path / "test_uploads")

        Config.ensure_directories()
        assert Path(Config.UPLOAD_FOLDER).exists()

        # Restore
        Config.UPLOAD_FOLDER = original_folder

    def test_ensure_directories_creates_log_dir(self, tmp_path):
        """Should create log directory if it doesn't exist."""
        original_dir = Config.LOG_DIR
        Config.LOG_DIR = str(tmp_path / "test_logs")

        Config.ensure_directories()
        assert Path(Config.LOG_DIR).exists()

        # Restore
        Config.LOG_DIR = original_dir

    def test_to_dict_returns_uppercase_attributes(self):
        """Should return only uppercase class attributes as dictionary."""
        config_dict = Config.to_dict()

        # Should include uppercase attributes
        assert "SECRET_KEY" in config_dict
        assert "ANTHROPIC_API_KEY" in config_dict
        assert "LOG_LEVEL" in config_dict

        # Should not include methods
        assert "validate" not in config_dict
        assert "from_cli_args" not in config_dict
        assert "to_dict" not in config_dict

        # Should not include private attributes
        assert "__dict__" not in config_dict


class TestArgumentParser:
    """Tests for argument parser creation."""

    def test_creates_argument_parser(self):
        """Should create argument parser with all expected arguments."""
        parser = Config.create_argument_parser()
        assert isinstance(parser, argparse.ArgumentParser)

        # Test that it can parse known arguments
        args = parser.parse_args(
            [
                "--host",
                "0.0.0.0",
                "--port",
                "8080",
                "--debug",
                "--api-key",
                "test-key",
                "--database",
                "sqlite:///test.db",
                "--upload-folder",
                "/tmp/uploads",
                "--log-level",
                "DEBUG",
                "--retention-days",
                "60",
            ]
        )

        assert args.host == "0.0.0.0"
        assert args.port == 8080
        assert args.debug is True
        assert args.api_key == "test-key"
        assert args.database == "sqlite:///test.db"
        assert args.upload_folder == "/tmp/uploads"
        assert args.log_level == "DEBUG"
        assert args.retention_days == 60

    def test_parser_has_help_text(self):
        """Should have help text for all arguments."""
        parser = Config.create_argument_parser()
        help_text = parser.format_help()

        # Should include all major argument groups
        assert "Server Options" in help_text
        assert "API Options" in help_text
        assert "Storage Options" in help_text
        assert "Logging Options" in help_text
        assert "Cleanup Options" in help_text

    def test_parser_allows_short_port_flag(self):
        """Should accept -p as short flag for port."""
        parser = Config.create_argument_parser()
        args = parser.parse_args(["-p", "9000"])
        assert args.port == 9000

    def test_parser_allows_short_debug_flag(self):
        """Should accept -d as short flag for debug."""
        parser = Config.create_argument_parser()
        args = parser.parse_args(["-d"])
        assert args.debug is True
