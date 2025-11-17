# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Claude AI service module.

This module provides functions for interacting with the Anthropic Claude API,
including model validation and text summarization.
"""

import time

from flask import current_app

from .logging_config import log_api_call


def get_anthropic_client():
    """
    Get the Anthropic client from the current Flask app context.

    Returns:
        Anthropic client instance

    Raises:
        RuntimeError: If no app context or client not initialized
    """
    if not current_app:
        raise RuntimeError("No Flask application context available")

    anthropic_ext = current_app.extensions.get("anthropic")
    if not anthropic_ext or not anthropic_ext.client:
        raise RuntimeError("Anthropic extension not initialized")

    return anthropic_ext.client


def validate_claude_model(app):
    """
    Validate that the configured Claude model is available.

    Makes a minimal test call to the API to verify the model exists
    and is accessible with the configured API key.

    In development mode, this validation is skipped as dummy API keys
    may be used for local testing.

    Args:
        app: Flask application instance

    Returns:
        bool: True if model is valid and accessible, False otherwise
    """
    model = app.config.get("CLAUDE_MODEL")
    anthropic_ext = app.extensions.get("anthropic")

    if not anthropic_ext or not anthropic_ext.client:
        app.logger.error("Anthropic client not initialized")
        return False

    # Skip validation in development mode
    flask_env = app.config.get("FLASK_ENV", "production")
    if flask_env == "development":
        app.logger.info(
            f"✓ Claude model '{model}' configured (validation skipped in development mode)"
        )
        return True

    try:
        # Make a minimal test call to validate the model exists
        anthropic_ext.client.messages.create(
            model=model,
            max_tokens=10,
            messages=[
                {
                    "role": "user",
                    "content": "test",
                }
            ],
        )
        app.logger.info(f"✓ Claude model '{model}' is available and accessible")
        return True
    except Exception as e:
        app.logger.error(f"✗ Claude model '{model}' validation failed: {str(e)}")
        app.logger.warning(
            "Please check your CLAUDE_MODEL environment variable or verify your API key"
        )
        return False


def summarize_with_claude(text, logger, prompt_text=None):
    """
    Summarize text using Anthropic Claude API.

    Args:
        text: Text content to summarize
        logger: Application logger instance
        prompt_text: Custom prompt text to use (optional, uses default if not provided)

    Returns:
        str: Generated summary text

    Raises:
        Exception: If API call fails or returns invalid response
    """
    start_time = time.time()

    try:
        client = get_anthropic_client()
        config = current_app.config

        model = config.get("CLAUDE_MODEL")
        max_tokens = config.get("MAX_TOKENS", 1024)
        max_text_length = config.get("MAX_TEXT_LENGTH", 100000)

        # Use provided prompt or fall back to default
        if prompt_text is None:
            prompt_text = config.get("DEFAULT_PROMPT_TEXT")

        # Use Claude model (configurable via environment variable)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt_text}\n\n{text[:max_text_length]}",
                }
            ],
        )

        duration = time.time() - start_time
        log_api_call(logger, "Claude Summarization", duration, success=True)

        # Extract text content from response, filtering for TextBlock types only
        for block in message.content:
            if hasattr(block, "text"):
                return block.text

        raise Exception("No text content in Claude response")

    except Exception as e:
        duration = time.time() - start_time
        log_api_call(logger, "Claude Summarization", duration, success=False, error=str(e))
        logger.error(f"Claude API error: {str(e)}")
        raise Exception(f"Error with Claude API: {str(e)}") from e
