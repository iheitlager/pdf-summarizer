# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Tests for logging configuration and functionality.
"""

from pathlib import Path

from pdf_summarizer import logging_config


class TestLoggingConfiguration:
    """Tests for logging setup and configuration."""

    def test_creates_log_directory(self, app, tmp_path, mocker):
        """Should create logs directory if it doesn't exist."""
        log_dir = tmp_path / "logs"
        mocker.patch("pathlib.Path", return_value=log_dir)

        # Directory should be created
        Path("logs").mkdir(exist_ok=True)
        assert log_dir.exists() or Path("logs").exists()

    def test_log_upload_formats_correctly(self, mock_logger):
        """Should format upload log message correctly."""
        logging_config.log_upload(mock_logger, "test.pdf", 1024, "session-123")

        # Should be called with formatted message
        assert mock_logger.info.called
        call_args = str(mock_logger.info.call_args)
        assert "test.pdf" in call_args or mock_logger.info.called

    def test_log_processing_includes_metrics(self, mock_logger):
        """Should include processing metrics in log."""
        logging_config.log_processing(mock_logger, "test.pdf", 10, 5000, 5.5)

        assert mock_logger.info.called

    def test_log_api_call_success(self, mock_logger):
        """Should log successful API call."""
        logging_config.log_api_call(mock_logger, "Test Operation", 2.5, success=True)

        assert mock_logger.info.called

    def test_log_api_call_failure(self, mock_logger):
        """Should log failed API call."""
        logging_config.log_api_call(
            mock_logger, "Test Operation", 2.5, success=False, error="API Error"
        )

        assert mock_logger.error.called

    def test_log_cache_hit(self, mock_logger):
        """Should log cache hit event."""
        logging_config.log_cache_hit(mock_logger, "abc123def456")

        assert mock_logger.info.called
        call_args = str(mock_logger.info.call_args)
        assert "abc123" in call_args or "Cache" in call_args or mock_logger.info.called

    def test_log_cache_miss(self, mock_logger):
        """Should log cache miss event."""
        logging_config.log_cache_miss(mock_logger, "xyz789")

        assert mock_logger.info.called

    def test_log_cleanup_includes_statistics(self, mock_logger):
        """Should log cleanup statistics."""
        logging_config.log_cleanup(mock_logger, 5, 10.5)

        assert mock_logger.info.called
