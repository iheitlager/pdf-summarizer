# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""Database models and SQLAlchemy instance for the PDF summarizer."""

from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy instance shared across application modules
# Initialized with the Flask app in pdf_summarizer.main
# http://flask-sqlalchemy.palletsprojects.com/en/3.1.x/
db = SQLAlchemy()


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
    summary_text = db.Column(db.Text, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    page_count = db.Column(db.Integer)
    char_count = db.Column(db.Integer)

    def __repr__(self) -> str:
        return f"<Summary for Upload {self.upload_id}>"


__all__ = ["db", "Upload", "Summary"]
