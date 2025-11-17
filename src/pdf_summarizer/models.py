# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""Database models and SQLAlchemy instance for the PDF summarizer."""

from datetime import UTC, datetime

from .extensions import db


class Upload(db.Model):  # type: ignore[name-defined]
    """Model representing an uploaded PDF file."""

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_hash = db.Column(
        db.String(64), index=True
    )  # SHA256 hash for caching (not unique - multiple uploads can share hash)
    session_id = db.Column(db.String(255), index=True)
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    file_size = db.Column(db.Integer)
    is_cached = db.Column(db.Boolean, default=False)
    summaries = db.relationship(
        "Summary", backref="upload", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Upload {self.original_filename}>"


class Summary(db.Model):  # type: ignore[name-defined]
    """Model representing a generated summary for an upload."""

    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("upload.id"), nullable=False)
    prompt_template_id = db.Column(
        db.Integer, db.ForeignKey("prompt_template.id"), nullable=True
    )
    summary_text = db.Column(db.Text, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    page_count = db.Column(db.Integer)
    char_count = db.Column(db.Integer)

    def __repr__(self) -> str:
        return f"<Summary for Upload {self.upload_id}>"


class PromptTemplate(db.Model):  # type: ignore[name-defined]
    """Model representing a reusable prompt template for summarization."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    modified_date = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    summaries = db.relationship(
        "Summary", backref="prompt_template", lazy=True, foreign_keys="Summary.prompt_template_id"
    )

    def __repr__(self) -> str:
        return f"<PromptTemplate {self.name}>"

    def validate(self) -> None:
        """Validate prompt template fields."""
        if not self.name or not self.name.strip():
            raise ValueError("Prompt template name cannot be empty")
        if not self.prompt_text or not self.prompt_text.strip():
            raise ValueError("Prompt text cannot be empty")
        if len(self.prompt_text) > 5000:
            raise ValueError("Prompt text cannot exceed 5000 characters")


__all__ = ["db", "Upload", "Summary", "PromptTemplate"]
