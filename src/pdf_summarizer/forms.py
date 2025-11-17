# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Flask-WTF forms module.

This module contains form definitions for the PDF Summarizer application,
including validation logic for file uploads.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import SubmitField
from wtforms.validators import ValidationError


class UploadForm(FlaskForm):
    """Form for uploading PDF files."""

    pdf_files = FileField(
        "PDF Files",
        validators=[FileRequired(), FileAllowed(["pdf"], "Only PDF files are allowed!")],
    )
    submit = SubmitField("Upload and Summarize")

    def validate_pdf_files(self, field):
        """
        Additional validation for file size.

        Args:
            field: The FileField being validated

        Raises:
            ValidationError: If file size exceeds 10MB
        """
        if field.data:
            # Check file size (werkzeug FileStorage object)
            field.data.seek(0, 2)  # Seek to end
            file_size = field.data.tell()
            field.data.seek(0)  # Reset to beginning

            if file_size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError("File size must not exceed 10MB")
