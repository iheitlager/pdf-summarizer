# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Main entry point for PDF Summarizer application.

This module provides the CLI entry point for running the application.
It uses the application factory pattern to create and configure the
Flask application instance.
"""

import sys

from dotenv import load_dotenv

# Load environment variables BEFORE importing any config modules
# This ensures Config class reads from .env file instead of environment
load_dotenv()

from pdf_summarizer.config import Config
from pdf_summarizer.factory import create_app


def main():
    """Main entry point for running the application."""

    # Validate configuration
    Config.from_cli_args()

    app = create_app(
        start_scheduler=not any("pytest" in arg or "conftest" in arg for arg in sys.argv)
    )

    # Run the application
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)


if __name__ == "__main__":
    main()
