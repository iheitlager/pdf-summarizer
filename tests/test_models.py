# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for database models (Upload and Summary).

Tests cover:
- Model creation and attributes
- Relationships between models
- Cascade deletion
- Database constraints
- Query operations
"""

from datetime import UTC, datetime

from pdf_summarizer.models import Summary, Upload


class TestUploadModel:
    """Tests for Upload database model."""

    def test_create_upload_with_all_fields(self, app, db):
        """Should create Upload with all fields populated."""
        with app.app_context():
            upload = Upload(
                filename="test_20231116_120000.pdf",
                original_filename="test.pdf",
                file_path="/uploads/test_20231116_120000.pdf",
                file_hash="abc123def456",
                session_id="session-123",
                file_size=2048,
                is_cached=False,
            )
            db.session.add(upload)
            db.session.commit()

            assert upload.id is not None
            assert upload.filename == "test_20231116_120000.pdf"
            assert upload.original_filename == "test.pdf"
            assert upload.file_hash == "abc123def456"
            assert upload.session_id == "session-123"
            assert upload.file_size == 2048
            assert upload.is_cached is False
            assert isinstance(upload.upload_date, datetime)

    def test_upload_default_values(self, app, db):
        """Should apply default values for upload_date and is_cached."""
        with app.app_context():
            upload = Upload(
                filename="test.pdf",
                original_filename="test.pdf",
                file_path="/uploads/test.pdf",
                session_id="session-1",
                file_size=1024,
            )
            db.session.add(upload)
            db.session.commit()

            assert upload.upload_date is not None
            assert upload.is_cached is False

    def test_upload_repr(self, app, db):
        """Should return readable string representation."""
        with app.app_context():
            upload = Upload(
                filename="test.pdf",
                original_filename="original.pdf",
                file_path="/uploads/test.pdf",
                session_id="session-1",
                file_size=1024,
            )
            db.session.add(upload)
            db.session.commit()

            repr_str = repr(upload)
            assert "Upload" in repr_str
            assert "original.pdf" in repr_str

    def test_file_hash_allows_duplicates_for_caching(self, app, db):
        """Should allow multiple uploads with same file_hash for caching."""
        with app.app_context():
            upload1 = Upload(
                filename="test1.pdf",
                original_filename="test1.pdf",
                file_path="/uploads/test1.pdf",
                file_hash="same_hash_for_caching",
                session_id="session-1",
                file_size=1024,
            )
            db.session.add(upload1)
            db.session.commit()

            # Second upload with same hash should succeed (cache hit scenario)
            upload2 = Upload(
                filename="test2.pdf",
                original_filename="test2.pdf",
                file_path="/uploads/test2.pdf",
                file_hash="same_hash_for_caching",
                session_id="session-2",
                file_size=2048,
                is_cached=True,
            )
            db.session.add(upload2)
            db.session.commit()

            # Both uploads should exist with same hash
            uploads = Upload.query.filter_by(file_hash="same_hash_for_caching").all()
            assert len(uploads) == 2
            assert uploads[0].file_hash == uploads[1].file_hash
            assert uploads[1].is_cached is True

    def test_query_by_session_id(self, app, db):
        """Should successfully query uploads by session_id."""
        with app.app_context():
            upload1 = Upload(
                filename="test1.pdf",
                original_filename="test1.pdf",
                file_path="/uploads/test1.pdf",
                session_id="session-A",
                file_size=1024,
            )
            upload2 = Upload(
                filename="test2.pdf",
                original_filename="test2.pdf",
                file_path="/uploads/test2.pdf",
                session_id="session-B",
                file_size=2048,
            )
            db.session.add_all([upload1, upload2])
            db.session.commit()

            results = Upload.query.filter_by(session_id="session-A").all()

            assert len(results) == 1
            assert results[0].filename == "test1.pdf"


class TestSummaryModel:
    """Tests for Summary database model."""

    def test_create_summary_with_all_fields(self, app, db, sample_upload):
        """Should create Summary with all fields populated."""
        with app.app_context():
            summary = Summary(
                upload_id=sample_upload.id,
                summary_text="This is a test summary.",
                page_count=5,
                char_count=1000,
            )
            db.session.add(summary)
            db.session.commit()

            assert summary.id is not None
            assert summary.upload_id == sample_upload.id
            assert summary.summary_text == "This is a test summary."
            assert summary.page_count == 5
            assert summary.char_count == 1000
            assert isinstance(summary.created_date, datetime)

    def test_summary_default_created_date(self, app, db, sample_upload):
        """Should set created_date to current time by default."""
        with app.app_context():
            summary = Summary(
                upload_id=sample_upload.id,
                summary_text="Test summary.",
                page_count=1,
                char_count=100,
            )
            db.session.add(summary)
            db.session.commit()

            assert summary.created_date is not None
            assert isinstance(summary.created_date, datetime)

    def test_summary_repr(self, app, db, sample_upload):
        """Should return readable string representation."""
        with app.app_context():
            summary = Summary(
                upload_id=sample_upload.id, summary_text="Test", page_count=1, char_count=100
            )
            db.session.add(summary)
            db.session.commit()

            repr_str = repr(summary)
            assert "Summary" in repr_str
            assert str(sample_upload.id) in repr_str


class TestUploadSummaryRelationship:
    """Tests for relationship between Upload and Summary models."""

    def test_upload_has_summaries_relationship(self, app, db, sample_upload):
        """Should access summaries through upload.summaries."""
        with app.app_context():
            # Re-fetch upload within this context
            upload = db.session.get(Upload, sample_upload.id)

            summary1 = Summary(
                upload_id=upload.id, summary_text="Summary 1", page_count=1, char_count=100
            )
            summary2 = Summary(
                upload_id=upload.id, summary_text="Summary 2", page_count=2, char_count=200
            )
            db.session.add_all([summary1, summary2])
            db.session.commit()

            db.session.refresh(upload)
            assert len(upload.summaries) == 2
            assert summary1 in upload.summaries
            assert summary2 in upload.summaries

    def test_summary_has_upload_backref(self, app, db, sample_upload, sample_summary):
        """Should access upload through summary.upload."""
        with app.app_context():
            # Re-fetch both objects within this context
            summary = db.session.get(Summary, sample_summary.id)
            upload = db.session.get(Upload, sample_upload.id)

            assert summary.upload is not None
            assert summary.upload.id == upload.id
            assert summary.upload.original_filename == upload.original_filename

    def test_cascade_delete_summaries(self, app, db, sample_upload):
        """Should cascade delete summaries when upload is deleted."""
        with app.app_context():
            # Re-fetch upload within this context
            upload = db.session.get(Upload, sample_upload.id)

            summary = Summary(
                upload_id=upload.id,
                summary_text="Test summary",
                page_count=1,
                char_count=100,
            )
            db.session.add(summary)
            db.session.commit()
            summary_id = summary.id

            # Delete upload
            db.session.delete(upload)
            db.session.commit()

            # Summary should be deleted
            deleted_summary = db.session.get(Summary, summary_id)
            assert deleted_summary is None

    def test_multiple_uploads_with_summaries(self, app, db):
        """Should handle multiple uploads each with their own summaries."""
        with app.app_context():
            upload1 = Upload(
                filename="test1.pdf",
                original_filename="test1.pdf",
                file_path="/uploads/test1.pdf",
                session_id="session-1",
                file_size=1024,
            )
            upload2 = Upload(
                filename="test2.pdf",
                original_filename="test2.pdf",
                file_path="/uploads/test2.pdf",
                session_id="session-2",
                file_size=2048,
            )
            db.session.add_all([upload1, upload2])
            db.session.flush()

            summary1 = Summary(
                upload_id=upload1.id,
                summary_text="Summary for upload 1",
                page_count=1,
                char_count=100,
            )
            summary2 = Summary(
                upload_id=upload2.id,
                summary_text="Summary for upload 2",
                page_count=2,
                char_count=200,
            )
            db.session.add_all([summary1, summary2])
            db.session.commit()

            db.session.refresh(upload1)
            db.session.refresh(upload2)

            assert len(upload1.summaries) == 1
            assert len(upload2.summaries) == 1
            assert upload1.summaries[0].summary_text == "Summary for upload 1"
            assert upload2.summaries[0].summary_text == "Summary for upload 2"


class TestDatabaseQueries:
    """Tests for common database query operations."""

    def test_order_uploads_by_date_descending(self, app, db):
        """Should order uploads by upload_date descending."""
        with app.app_context():
            from datetime import timedelta

            upload1 = Upload(
                filename="old.pdf",
                original_filename="old.pdf",
                file_path="/uploads/old.pdf",
                session_id="session-1",
                file_size=1024,
                upload_date=datetime.now(UTC) - timedelta(days=2),
            )
            upload2 = Upload(
                filename="new.pdf",
                original_filename="new.pdf",
                file_path="/uploads/new.pdf",
                session_id="session-2",
                file_size=2048,
                upload_date=datetime.now(UTC),
            )
            db.session.add_all([upload1, upload2])
            db.session.commit()

            results = Upload.query.order_by(Upload.upload_date.desc()).all()

            assert results[0].original_filename == "new.pdf"
            assert results[1].original_filename == "old.pdf"

    def test_filter_uploads_by_multiple_criteria(self, app, db):
        """Should filter uploads by multiple criteria."""
        with app.app_context():
            upload1 = Upload(
                filename="cached.pdf",
                original_filename="cached.pdf",
                file_path="/uploads/cached.pdf",
                session_id="session-1",
                file_size=1024,
                is_cached=True,
            )
            upload2 = Upload(
                filename="processed.pdf",
                original_filename="processed.pdf",
                file_path="/uploads/processed.pdf",
                session_id="session-1",
                file_size=2048,
                is_cached=False,
            )
            db.session.add_all([upload1, upload2])
            db.session.commit()

            results = Upload.query.filter_by(session_id="session-1", is_cached=True).all()

            assert len(results) == 1
            assert results[0].original_filename == "cached.pdf"
