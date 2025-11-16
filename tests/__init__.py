# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Test suite for PDF Summarizer application.

This package contains comprehensive tests for all application components:
- Unit tests for helper functions
- Integration tests for routes
- Database model tests
- Caching and session tests
- End-to-end workflow tests
"""

from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def _create_sample_pdf():
    """Helper function to create a fresh sample PDF."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Test PDF Document")
    c.drawString(100, 730, "This is a sample PDF file for testing.")
    c.drawString(100, 710, "It contains multiple lines of text.")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


__all__ = ["_create_sample_pdf"]
