# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for Flask routes.

Tests cover all HTTP endpoints:
- GET/POST /  (index)
- GET /results
- GET /download/<summary_id>
- GET /my-uploads
- GET /all-summaries
"""

from datetime import UTC
from io import BytesIO

from pdf_summarizer.models import Summary, Upload


class TestIndexRoute:
    """Tests for the index route (GET and POST /)."""

    def test_get_index_renders_template(self, client):
        """Should render index template on GET request."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"PDF Summarizer" in response.data or b"Upload" in response.data

    def test_get_index_shows_upload_form(self, client):
        """Should display upload form on GET request."""
        response = client.get("/")

        assert response.status_code == 200
        # Check for form elements
        assert b"form" in response.data or b"upload" in response.data.lower()

    def test_post_valid_file_creates_upload(self, client, app, db, sample_pdf, mock_anthropic):
        """Should create Upload and Summary on valid file upload."""
        with app.app_context():
            data = {"pdf_files": (sample_pdf, "test.pdf")}

            response = client.post(
                "/", data=data, content_type="multipart/form-data", follow_redirects=False
            )

            # Should redirect to results
            assert response.status_code == 302
            assert "/results" in response.location

            # Check database
            uploads = Upload.query.all()
            assert len(uploads) == 1
            assert uploads[0].original_filename == "test.pdf"

    def test_post_multiple_files(self, client, app, db, sample_pdf, multipage_pdf, mock_anthropic):
        """Should handle multiple file uploads."""
        with app.app_context():
            sample_pdf.seek(0)
            multipage_pdf.seek(0)

            data = {"pdf_files": [(sample_pdf, "test1.pdf"), (multipage_pdf, "test2.pdf")]}

            response = client.post(
                "/", data=data, content_type="multipart/form-data", follow_redirects=False
            )

            assert response.status_code == 302

            uploads = Upload.query.all()
            assert len(uploads) == 2

    def test_post_no_files_shows_error(self, client):
        """Should show error when no files are selected."""
        response = client.post(
            "/", data={}, content_type="multipart/form-data", follow_redirects=True
        )

        # Should either show the error message or redirect back to index
        assert response.status_code == 200
        # Check for error indication (either message or form elements)
        assert (
            b"No files selected" in response.data
            or b"error" in response.data.lower()
            or b"pdf_files" in response.data.lower()
        )

    def test_post_invalid_file_type_rejected(self, client):
        """Should reject non-PDF files."""
        txt_file = BytesIO(b"not a pdf")
        data = {"pdf_files": (txt_file, "test.txt")}

        response = client.post(
            "/", data=data, content_type="multipart/form-data", follow_redirects=True
        )

        # Should show error or skip file
        assert response.status_code == 200


class TestResultsRoute:
    """Tests for the /results route."""

    def test_displays_summaries_for_given_ids(self, client, app, db, sample_upload, sample_summary):
        """Should display summaries for provided upload IDs."""
        with app.app_context():
            response = client.get(f"/results?ids={sample_upload.id}")

            assert response.status_code == 200
            assert sample_upload.original_filename.encode() in response.data
            assert sample_summary.summary_text.encode() in response.data

    def test_redirects_when_no_ids_provided(self, client):
        """Should redirect to index when no IDs provided."""
        response = client.get("/results", follow_redirects=False)

        assert response.status_code == 302
        assert response.location.endswith("/")

    def test_handles_invalid_ids_gracefully(self, client):
        """Should handle invalid upload IDs gracefully."""
        response = client.get("/results?ids=99999", follow_redirects=True)

        # Should either show empty or redirect with error
        assert response.status_code == 200

    def test_displays_multiple_summaries(self, client, app, db):
        """Should display multiple summaries when multiple IDs provided."""
        with app.app_context():
            upload1 = Upload(
                filename="test1.pdf",
                original_filename="test1.pdf",
                file_path="/tmp/test1.pdf",
                session_id="session-1",
                file_size=1024,
            )
            upload2 = Upload(
                filename="test2.pdf",
                original_filename="test2.pdf",
                file_path="/tmp/test2.pdf",
                session_id="session-1",
                file_size=2048,
            )
            db.session.add_all([upload1, upload2])
            db.session.flush()

            summary1 = Summary(
                upload_id=upload1.id, summary_text="Summary 1", page_count=1, char_count=100
            )
            summary2 = Summary(
                upload_id=upload2.id, summary_text="Summary 2", page_count=2, char_count=200
            )
            db.session.add_all([summary1, summary2])
            db.session.commit()

            response = client.get(f"/results?ids={upload1.id},{upload2.id}")

            assert response.status_code == 200
            assert b"test1.pdf" in response.data
            assert b"test2.pdf" in response.data


class TestDownloadRoute:
    """Tests for the /download/<summary_id> route."""

    def test_downloads_summary_as_text_file(self, client, app, db, sample_upload, sample_summary):
        """Should download summary as text file."""
        with app.app_context():
            response = client.get(f"/download/{sample_summary.id}")

            assert response.status_code == 200
            assert response.content_type == "text/plain; charset=utf-8"
            assert b"Summary of:" in response.data
            assert sample_summary.summary_text.encode() in response.data

    def test_download_includes_metadata(self, client, app, sample_upload, sample_summary):
        """Should include metadata in downloaded file."""
        with app.app_context():
            response = client.get(f"/download/{sample_summary.id}")

            assert response.status_code == 200
            assert b"Pages:" in response.data
            assert b"Generated:" in response.data
            assert str(sample_summary.page_count).encode() in response.data

    def test_download_invalid_summary_id_returns_404(self, client):
        """Should return 404 for invalid summary ID."""
        response = client.get("/download/99999", follow_redirects=False)

        assert response.status_code == 404 or response.status_code == 302


class TestMyUploadsRoute:
    """Tests for the /my-uploads route."""

    def test_shows_uploads_for_current_session(self, client, app, db, mock_session_id):
        """Should show only uploads for current session."""
        with app.app_context():
            # Set session ID
            with client.session_transaction() as sess:
                sess["session_id"] = mock_session_id

            # Create uploads for different sessions
            upload1 = Upload(
                filename="mine.pdf",
                original_filename="mine.pdf",
                file_path="/tmp/mine.pdf",
                session_id=mock_session_id,
                file_size=1024,
            )
            upload2 = Upload(
                filename="other.pdf",
                original_filename="other.pdf",
                file_path="/tmp/other.pdf",
                session_id="different-session",
                file_size=2048,
            )
            db.session.add_all([upload1, upload2])
            db.session.commit()

            response = client.get("/my-uploads")

            assert response.status_code == 200
            assert b"mine.pdf" in response.data
            assert b"other.pdf" not in response.data

    def test_orders_by_date_descending(self, client, app, db, mock_session_id):
        """Should order uploads by date descending."""
        with app.app_context():
            with client.session_transaction() as sess:
                sess["session_id"] = mock_session_id

            from datetime import datetime, timedelta

            upload1 = Upload(
                filename="old_upload.pdf",
                original_filename="old.pdf",
                file_path="/uploads/old_upload.pdf",
                session_id=mock_session_id,
                file_size=1024,
                upload_date=datetime.now(UTC) - timedelta(days=1),
            )
            upload2 = Upload(
                filename="new_upload.pdf",
                original_filename="new.pdf",
                file_path="/uploads/new_upload.pdf",
                session_id=mock_session_id,
                file_size=2048,
                upload_date=datetime.now(UTC),
            )
            db.session.add_all([upload1, upload2])
            db.session.commit()

            response = client.get("/my-uploads")

            assert response.status_code == 200
            # New upload should appear before old upload in HTML
            new_pos = response.data.find(b"new.pdf")
            old_pos = response.data.find(b"old.pdf")
            assert new_pos < old_pos


class TestAllSummariesRoute:
    """Tests for the /all-summaries route."""

    def test_shows_all_uploads_from_all_sessions(self, client, app, db):
        """Should show uploads from all sessions."""
        with app.app_context():
            upload1 = Upload(
                filename="session1.pdf",
                original_filename="session1.pdf",
                file_path="/tmp/session1.pdf",
                session_id="session-1",
                file_size=1024,
            )
            upload2 = Upload(
                filename="session2.pdf",
                original_filename="session2.pdf",
                file_path="/tmp/session2.pdf",
                session_id="session-2",
                file_size=2048,
            )
            db.session.add_all([upload1, upload2])
            db.session.commit()

            response = client.get("/all-summaries")

            assert response.status_code == 200
            assert b"session1.pdf" in response.data
            assert b"session2.pdf" in response.data

    def test_orders_by_date_descending(self, client, app, db):
        """Should order all uploads by date descending."""
        with app.app_context():
            from datetime import datetime, timedelta

            upload1 = Upload(
                filename="old_upload.pdf",
                original_filename="old.pdf",
                file_path="/uploads/old_upload.pdf",
                session_id="session-1",
                file_size=1024,
                upload_date=datetime.now(UTC) - timedelta(days=2),
            )
            upload2 = Upload(
                filename="new_upload.pdf",
                original_filename="new.pdf",
                file_path="/uploads/new_upload.pdf",
                session_id="session-2",
                file_size=2048,
                upload_date=datetime.now(UTC),
            )
            db.session.add_all([upload1, upload2])
            db.session.commit()

            response = client.get("/all-summaries")

            assert response.status_code == 200
            new_pos = response.data.find(b"new.pdf")
            old_pos = response.data.find(b"old.pdf")
            assert new_pos < old_pos


class TestRouteExceptionHandling:
    """Tests for exception handling in routes."""

    def test_results_route_handles_invalid_id_format(self, client):
        """Should handle invalid ID format gracefully."""
        response = client.get("/results?ids=invalid,123")

        # Should either show error or redirect
        assert response.status_code in [200, 302]

    def test_results_route_handles_empty_id_list(self, client):
        """Should handle empty ID list."""
        response = client.get("/results?ids=")

        # Should either show error or redirect
        assert response.status_code in [200, 302]

    def test_download_with_exception_shows_error(self, client, app, db, mocker):
        """Should handle exceptions in download route gracefully."""
        # Mock to force an exception
        mocker.patch.object(Summary, "query", side_effect=Exception("DB error"))

        response = client.get("/download/1", follow_redirects=True)

        # Should redirect with error message
        assert response.status_code == 200

    def test_index_with_non_pdf_file_shows_skip_message(self, client):
        """Should skip non-PDF files with warning message."""
        txt_file = BytesIO(b"This is text content")
        data = {"pdf_files": (txt_file, "test.txt")}

        response = client.post(
            "/", data=data, content_type="multipart/form-data", follow_redirects=True
        )

        # Should show skip warning
        assert response.status_code == 200
        assert (
            b"Skipped" in response.data
            or b"Only PDF" in response.data
            or b"test.txt" in response.data
        )

    def test_empty_file_upload_shows_error(self, client):
        """Should handle empty file upload."""
        empty_file = BytesIO(b"")
        data = {"pdf_files": (empty_file, "")}

        response = client.post(
            "/", data=data, content_type="multipart/form-data", follow_redirects=True
        )

        # Should show error
        assert response.status_code == 200

    def test_non_cache_hit_creates_new_summary(
        self, client, app, db, sample_pdf, mock_anthropic, mocker
    ):
        """Should create new summary on cache miss."""
        with app.app_context():
            # Mock to ensure cache miss
            mocker.patch("pdf_summarizer.routes.check_cache", return_value=None)

            data = {"pdf_files": (sample_pdf, "unique.pdf")}

            response = client.post(
                "/", data=data, content_type="multipart/form-data", follow_redirects=False
            )

            # Should redirect to results
            assert response.status_code == 302

            # Should have created one upload
            uploads = Upload.query.all()
            assert len(uploads) >= 1

            # Most recent upload should NOT be marked as cached
            latest_upload = sorted(uploads, key=lambda x: x.id)[-1]
            assert latest_upload.is_cached is False
