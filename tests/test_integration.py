# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
End-to-end integration tests for complete workflows.

Tests cover:
- Complete upload → process → view → download flow
- Multi-user scenarios
- Cache workflows
- Error recovery
"""

from pdf_summarizer.extensions import limiter
from pdf_summarizer.models import Upload
from tests import _create_sample_pdf


class TestCompleteUploadWorkflow:
    """Tests for complete end-to-end upload workflow."""

    def test_full_upload_process_view_download_flow(self, client, app, db, mock_anthropic):
        """Should complete full workflow: upload → process → view → download."""
        with app.app_context():
            # 1. Upload PDF
            pdf = _create_sample_pdf()
            response = client.post(
                "/",
                data={"pdf_files": (pdf, "test.pdf")},
                content_type="multipart/form-data",
                follow_redirects=False,
            )

            assert response.status_code == 302
            assert "/results" in response.location

            # 2. Extract upload ID from redirect
            upload = Upload.query.first()
            assert upload is not None

            # 3. View results
            response = client.get(f"/results?ids={upload.id}")
            assert response.status_code == 200
            assert upload.original_filename.encode() in response.data

            # 4. Download summary
            summary = upload.summaries[0]
            response = client.get(f"/download/{summary.id}")
            assert response.status_code == 200
            assert response.content_type == "text/plain; charset=utf-8"
            assert summary.summary_text.encode() in response.data

    def test_multi_file_upload_workflow(self, client, app, db, mock_anthropic):
        """Should handle multiple file upload workflow."""
        with app.app_context():
            pdf1 = _create_sample_pdf()
            pdf2 = _create_sample_pdf()

            response = client.post(
                "/",
                data={"pdf_files": [(pdf1, "test1.pdf"), (pdf2, "test2.pdf")]},
                content_type="multipart/form-data",
                follow_redirects=False,
            )

            assert response.status_code == 302

            uploads = Upload.query.all()
            assert len(uploads) == 2

            # Both should have summaries
            for upload in uploads:
                assert len(upload.summaries) > 0

    def test_cache_workflow_same_file_twice(self, client, app, db, mock_anthropic, mocker):
        """Should use cache when same file uploaded twice."""
        with app.app_context():
            # Mock file hash to return consistent value
            test_hash = "consistent_hash_123"
            mocker.patch("pdf_summarizer.routes.calculate_file_hash", return_value=test_hash)

            # First upload
            pdf1 = _create_sample_pdf()
            client.post(
                "/",
                data={"pdf_files": (pdf1, "first.pdf")},
                content_type="multipart/form-data",
            )

            # Second upload (same file)
            pdf2 = _create_sample_pdf()
            client.post(
                "/",
                data={"pdf_files": (pdf2, "second.pdf")},
                content_type="multipart/form-data",
            )

            # Should have two uploads but API called only once (cache hit on second)
            uploads = Upload.query.all()
            assert len(uploads) == 2

            # Second upload should be marked as cached
            second_upload = Upload.query.filter_by(original_filename="second.pdf").first()
            assert second_upload.is_cached is True


class TestConcurrentUserScenarios:
    """Tests for scenarios with multiple concurrent users."""

    def test_concurrent_uploads_from_different_sessions(self, app, db, mock_anthropic):
        """Should handle uploads from different sessions concurrently."""
        with app.app_context():
            client1 = app.test_client()
            client1_limiter = limiter
            client1_limiter.enabled = False

            client2 = app.test_client()
            client2_limiter = limiter
            client2_limiter.enabled = False

            pdf1 = _create_sample_pdf()
            response1 = client1.post(
                "/",
                data={"pdf_files": (pdf1, "user1.pdf")},
                content_type="multipart/form-data",
            )

            pdf2 = _create_sample_pdf()
            response2 = client2.post(
                "/",
                data={"pdf_files": (pdf2, "user2.pdf")},
                content_type="multipart/form-data",
            )

            # Both should succeed
            assert response1.status_code == 302
            assert response2.status_code == 302

            # Should have 2 uploads with different sessions
            uploads = Upload.query.all()
            assert len(uploads) == 2
            assert uploads[0].session_id != uploads[1].session_id

    def test_my_uploads_shows_only_user_files(self, app, db, mock_anthropic):
        """Should show only current user's uploads in My Uploads."""
        with app.app_context():
            client1 = app.test_client()
            client1_limiter = limiter
            client1_limiter.enabled = False

            client2 = app.test_client()
            client2_limiter = limiter
            client2_limiter.enabled = False

            # User 1 upload
            pdf1 = _create_sample_pdf()
            client1.post(
                "/",
                data={"pdf_files": (pdf1, "user1.pdf")},
                content_type="multipart/form-data",
            )

            # User 2 upload
            pdf2 = _create_sample_pdf()
            client2.post(
                "/",
                data={"pdf_files": (pdf2, "user2.pdf")},
                content_type="multipart/form-data",
            )

            # User 1 views their uploads
            response1 = client1.get("/my-uploads")
            assert b"user1.pdf" in response1.data
            assert b"user2.pdf" not in response1.data

            # User 2 views their uploads
            response2 = client2.get("/my-uploads")
            assert b"user2.pdf" in response2.data
            assert b"user1.pdf" not in response2.data


class TestErrorRecovery:
    """Tests for error handling and recovery scenarios."""

    def test_recovery_from_failed_upload(self, client, app, db, mock_anthropic, mocker):
        """Should handle failed upload and allow retry."""
        with app.app_context():
            # First attempt fails
            mocker.patch(
                "pdf_summarizer.routes.summarize_with_claude", side_effect=Exception("API Error")
            )

            pdf1 = _create_sample_pdf()
            response1 = client.post(
                "/",
                data={"pdf_files": (pdf1, "test.pdf")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )

            # Should show error
            assert b"Error" in response1.data or b"error" in response1.data.lower()

            # Retry succeeds
            mocker.patch(
                "pdf_summarizer.routes.summarize_with_claude", return_value="Success summary"
            )

            pdf2 = _create_sample_pdf()
            response2 = client.post(
                "/",
                data={"pdf_files": (pdf2, "test.pdf")},
                content_type="multipart/form-data",
                follow_redirects=False,
            )

            # Should succeed
            assert response2.status_code == 302

    def test_database_integrity_across_operations(
        self, client, app, db, sample_pdf, mock_anthropic
    ):
        """Should maintain database integrity across multiple operations."""
        with app.app_context():
            # Upload
            sample_pdf.seek(0)
            client.post(
                "/",
                data={"pdf_files": (sample_pdf, "test.pdf")},
                content_type="multipart/form-data",
            )

            upload = Upload.query.first()
            summary = upload.summaries[0]

            # View results multiple times
            for _ in range(5):
                response = client.get(f"/results?ids={upload.id}")
                assert response.status_code == 200

            # Download multiple times
            for _ in range(5):
                response = client.get(f"/download/{summary.id}")
                assert response.status_code == 200

            # Database should still be consistent
            db.session.refresh(upload)
            assert len(upload.summaries) == 1
            assert upload.summaries[0].id == summary.id
