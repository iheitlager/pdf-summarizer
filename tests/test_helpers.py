# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for helper functions in main.py

Tests cover:
- calculate_file_hash()
- check_cache()
- extract_text_from_pdf()
- summarize_with_claude()
- save_uploaded_file()
- cleanup_old_uploads()
- get_or_create_session_id()
"""

import os
from datetime import UTC, datetime, timedelta

import pytest
from werkzeug.datastructures import FileStorage

from pdf_summarizer import utils
from pdf_summarizer.claude_service import summarize_with_claude
from pdf_summarizer.cleanup import cleanup_old_uploads
from pdf_summarizer.models import Upload
from pdf_summarizer.routes import check_cache, get_or_create_session_id


class TestCalculateFileHash:
    """Tests for file hash calculation function."""

    def test_generates_valid_sha256_hash(self, tmp_path):
        """Should generate a valid 64-character SHA256 hash."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content")

        file_hash = utils.calculate_file_hash(str(test_file))

        assert len(file_hash) == 64
        assert all(c in "0123456789abcdef" for c in file_hash)

    def test_same_content_produces_same_hash(self, tmp_path):
        """Should produce consistent hash for identical content."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content")

        hash1 = utils.calculate_file_hash(str(test_file))
        hash2 = utils.calculate_file_hash(str(test_file))

        assert hash1 == hash2

    def test_different_content_produces_different_hashes(self, tmp_path):
        """Should produce different hashes for different content."""
        file1 = tmp_path / "test1.pdf"
        file2 = tmp_path / "test2.pdf"
        file1.write_bytes(b"content 1")
        file2.write_bytes(b"content 2")

        hash1 = utils.calculate_file_hash(str(file1))
        hash2 = utils.calculate_file_hash(str(file2))

        assert hash1 != hash2

    def test_handles_large_files(self, tmp_path):
        """Should handle large files with chunked reading."""
        test_file = tmp_path / "large.pdf"
        # Create 1MB file
        test_file.write_bytes(b"x" * (1024 * 1024))

        file_hash = utils.calculate_file_hash(str(test_file))

        assert len(file_hash) == 64


class TestCheckCache:
    """Tests for cache checking function."""

    def test_returns_upload_when_cached(self, app, db, cached_upload):
        """Should return upload when hash exists with summary."""
        with app.app_context():
            result = check_cache(cached_upload.file_hash)

            assert result is not None
            assert result.id == cached_upload.id
            assert len(result.summaries) > 0

    def test_returns_none_when_not_cached(self, app):
        """Should return None when hash doesn't exist."""
        with app.app_context():
            result = check_cache("nonexistent_hash_12345")

            assert result is None

    def test_returns_none_when_upload_has_no_summary(self, app, db):
        """Should return None when upload exists but has no summary."""
        with app.app_context():
            upload = Upload(
                filename="test.pdf",
                original_filename="test.pdf",
                file_path="/tmp/test.pdf",
                file_hash="orphan_hash",
                session_id="test-session",
                file_size=1024,
            )
            db.session.add(upload)
            db.session.commit()

            result = check_cache("orphan_hash")

            assert result is None


class TestExtractTextFromPDF:
    """Tests for PDF text extraction function."""

    def test_extracts_text_from_valid_pdf(self, app, tmp_path, sample_pdf):
        """Should successfully extract text from valid PDF."""
        with app.app_context():
            pdf_file = tmp_path / "test.pdf"
            pdf_file.write_bytes(sample_pdf.read())

            text, page_count = utils.extract_text_from_pdf(str(pdf_file), app.logger)

            assert isinstance(text, str)
            assert len(text) > 0
            assert page_count == 1

    def test_extracts_text_from_multipage_pdf(self, app, tmp_path, multipage_pdf):
        """Should extract text from multi-page PDF and return correct count."""
        with app.app_context():
            pdf_file = tmp_path / "multi.pdf"
            pdf_file.write_bytes(multipage_pdf.read())

            text, page_count = utils.extract_text_from_pdf(str(pdf_file), app.logger)

            assert isinstance(text, str)
            assert page_count == 3

    def test_raises_exception_for_corrupted_pdf(self, app, tmp_path, corrupted_pdf):
        """Should raise exception for corrupted PDF."""
        with app.app_context():
            pdf_file = tmp_path / "corrupted.pdf"
            pdf_file.write_bytes(corrupted_pdf.read())

            with pytest.raises(Exception) as exc_info:
                utils.extract_text_from_pdf(str(pdf_file), app.logger)

            assert "Error reading PDF" in str(exc_info.value)


class TestSummarizeWithClaude:
    """Tests for Claude API summarization function."""

    def test_returns_summary_text(self, app, mock_anthropic):
        """Should return summary text from Claude API."""
        with app.app_context():
            text = "This is a test document with some content."

            summary = summarize_with_claude(text, app.logger, app.logger)

            assert isinstance(summary, str)
            assert len(summary) > 0
            assert summary == "This is a test summary of the document."
            mock_anthropic.assert_called_once()

    def test_truncates_long_text(self, app, mock_anthropic):
        """Should truncate text to 100k characters before API call."""
        with app.app_context():
            # Create text longer than 100k characters
            long_text = "x" * 150000

            summarize_with_claude(long_text, app.logger, app.logger)

            # Verify API was called with truncated text
            call_args = mock_anthropic.call_args
            content = call_args[1]["messages"][0]["content"]
            assert len(content) <= 100000 + 200  # Allow for prompt text

    def test_raises_exception_on_api_error(self, app, mocker):
        """Should raise exception when API call fails."""
        with app.app_context():
            # Get the anthropic client from the app extensions
            anthropic_ext = app.extensions.get("anthropic")
            mocker.patch.object(
                anthropic_ext.client.messages, "create", side_effect=Exception("API Error")
            )

            with pytest.raises(Exception) as exc_info:
                summarize_with_claude("test text", app.logger, app.logger)

            assert "Error with Claude API" in str(exc_info.value)


class TestSaveUploadedFile:
    """Tests for file upload saving function."""

    def test_creates_secure_filename(self, app, tmp_path, sample_pdf, mocker):
        """Should create secure filename with timestamp."""
        with app.app_context():
            file_storage = FileStorage(
                stream=sample_pdf, filename="test file.pdf", content_type="application/pdf"
            )

            file_path, unique_filename, original_filename, file_size = utils.save_uploaded_file(
                file_storage, str(tmp_path)
            )

            assert original_filename == "test file.pdf"
            assert "test_file" in unique_filename
            assert unique_filename.endswith(".pdf")
            assert "_" in unique_filename  # Contains timestamp
            assert file_size > 0

    def test_saves_file_to_correct_location(self, app, sample_pdf):
        """Should save file to upload folder."""
        with app.app_context():
            file_storage = FileStorage(
                stream=sample_pdf, filename="test.pdf", content_type="application/pdf"
            )

            file_path, _, _, _ = utils.save_uploaded_file(file_storage, app.config["UPLOAD_FOLDER"])

            # File should exist and be in uploads folder
            assert os.path.exists(file_path)
            assert "uploads" in file_path
            assert file_path.endswith(".pdf")

    def test_handles_special_characters_in_filename(self, app, sample_pdf):
        """Should sanitize filenames with special characters."""
        with app.app_context():
            file_storage = FileStorage(
                stream=sample_pdf,
                filename="../../../etc/passwd.pdf",
                content_type="application/pdf",
            )

            _, unique_filename, _, _ = utils.save_uploaded_file(
                file_storage, app.config["UPLOAD_FOLDER"]
            )

            # Filename should be sanitized
            assert "../" not in unique_filename
            assert ".." not in unique_filename


class TestCleanupOldUploads:
    """Tests for cleanup job function."""

    def test_deletes_uploads_older_than_retention_period(self, app, db, tmp_path, mocker):
        """Should delete uploads older than retention days."""
        with app.app_context():
            mocker.patch.dict(os.environ, {"RETENTION_DAYS": "30"})

            # Create old upload
            old_date = datetime.now(UTC) - timedelta(days=31)
            old_upload = Upload(
                filename="old.pdf",
                original_filename="old.pdf",
                file_path=str(tmp_path / "old.pdf"),
                file_hash="old_hash",
                session_id="test",
                file_size=1024,
                upload_date=old_date,
            )
            db.session.add(old_upload)

            # Create recent upload
            recent_upload = Upload(
                filename="recent.pdf",
                original_filename="recent.pdf",
                file_path=str(tmp_path / "recent.pdf"),
                file_hash="recent_hash",
                session_id="test",
                file_size=1024,
            )
            db.session.add(recent_upload)
            db.session.commit()

            # Create files
            (tmp_path / "old.pdf").write_bytes(b"old")
            (tmp_path / "recent.pdf").write_bytes(b"recent")

            cleanup_old_uploads(app)

            # Verify old upload deleted, recent kept
            assert db.session.get(Upload, old_upload.id) is None
            assert db.session.get(Upload, recent_upload.id) is not None

    def test_handles_missing_files_gracefully(self, app, db, mocker):
        """Should handle case where file doesn't exist on disk."""
        with app.app_context():
            mocker.patch.dict(os.environ, {"RETENTION_DAYS": "30"})

            old_date = datetime.now(UTC) - timedelta(days=31)
            upload = Upload(
                filename="missing.pdf",
                original_filename="missing.pdf",
                file_path="/nonexistent/path/missing.pdf",
                file_hash="missing_hash",
                session_id="test",
                file_size=1024,
                upload_date=old_date,
            )
            db.session.add(upload)
            db.session.commit()

            # Should not raise exception
            cleanup_old_uploads(app)

            # Upload should still be deleted from database
            assert db.session.get(Upload, upload.id) is None


class TestGetOrCreateSessionId:
    """Tests for session ID management function."""

    def test_creates_new_session_id_if_not_exists(self, app, client):
        """Should create new session ID on first call."""
        with app.app_context():
            with client.session_transaction() as sess:
                # Ensure no session ID exists
                sess.pop("session_id", None)

            with client:
                client.get("/")
                session_id = get_or_create_session_id()

                assert session_id is not None
                assert len(session_id) > 0

    def test_returns_existing_session_id(self, app, client, mock_session_id):
        """Should return existing session ID if present."""
        with app.app_context():
            with client.session_transaction() as sess:
                sess["session_id"] = mock_session_id

            with client:
                client.get("/")
                session_id = get_or_create_session_id()

                assert session_id == mock_session_id

    def test_session_id_is_valid_uuid_format(self, app, client):
        """Should generate valid UUID format."""
        with app.app_context():
            with client:
                client.get("/")
                session_id = get_or_create_session_id()

                # UUID format: 8-4-4-4-12
                parts = session_id.split("-")
                assert len(parts) == 5
                assert len(parts[0]) == 8
                assert len(parts[1]) == 4
                assert len(parts[2]) == 4
                assert len(parts[3]) == 4
                assert len(parts[4]) == 12
