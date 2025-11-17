# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Flask-WTF forms module.

This module contains form definitions for the PDF Summarizer application,
including validation logic for file uploads.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError


class UploadForm(FlaskForm):
    """Form for uploading PDF files."""

    pdf_files = FileField(
        "PDF Files",
        validators=[FileRequired(), FileAllowed(["pdf"], "Only PDF files are allowed!")],
    )
    prompt_template = SelectField(
        "Prompt Template",
        coerce=int,
        validators=[DataRequired()],
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


class PromptTemplateForm(FlaskForm):
    """Form for creating and editing prompt templates."""

    name = StringField(
        "Template Name",
        validators=[
            DataRequired(message="Template name is required"),
            Length(min=1, max=100, message="Name must be between 1 and 100 characters"),
        ],
    )
    prompt_text = TextAreaField(
        "Prompt Text",
        validators=[
            DataRequired(message="Prompt text is required"),
            Length(min=1, max=5000, message="Prompt text must be between 1 and 5000 characters"),
        ],
        render_kw={"rows": 10, "placeholder": "Enter the prompt text for summarization..."},
    )
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Template")
