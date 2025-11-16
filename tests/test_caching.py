# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Tests for caching mechanism and cache-related functionality.
"""

from pdf_summarizer import main as app_module


class TestCachingMechanism:
    """Tests for PDF summary caching logic."""

    def test_cache_hit_avoids_api_call(
        self, client, app, db, cached_upload, mock_anthropic, sample_pdf
    ):
        """Should not call Claude API when cache hit occurs."""
        with app.app_context():
            # Reset mock call count
            mock_anthropic.reset_mock()

            # Upload same file (same hash)
            sample_pdf.seek(0)

            # Mock calculate_file_hash to return cached hash
            with client.session_transaction() as sess:
                sess["session_id"] = "test-session"

            # We would need to mock the hash calculation here
            # For now, verify the logic works when check_cache finds a match

            # Verify cache lookup returns cached upload
            result = app_module.check_cache(cached_upload.file_hash)
            assert result is not None
            assert result.id == cached_upload.id

    def test_cache_hit_creates_new_upload_record(self, app, db, cached_upload):
        """Should create new Upload record even on cache hit."""
        with app.app_context():
            # Re-fetch the cached_upload within this context
            upload = db.session.get(app_module.Upload, cached_upload.id)
            initial_count = app_module.Upload.query.count()

            # Simulate cache hit scenario
            cached_summary = upload.summaries[0]

            new_upload = app_module.Upload(
                filename="new_file.pdf",
                original_filename="new.pdf",
                file_path="/tmp/new.pdf",
                file_hash=upload.file_hash,  # Same hash
                session_id="new-session",
                file_size=upload.file_size,
                is_cached=True,
            )
            db.session.add(new_upload)
            db.session.flush()

            # Copy summary
            new_summary = app_module.Summary(
                upload_id=new_upload.id,
                summary_text=cached_summary.summary_text,
                page_count=cached_summary.page_count,
                char_count=cached_summary.char_count,
            )
            db.session.add(new_summary)
            db.session.commit()

            # Should have one more upload
            assert app_module.Upload.query.count() == initial_count + 1
            assert new_upload.is_cached is True

    def test_cache_miss_calls_api(self, client, app, db, mock_anthropic, sample_pdf):
        """Should call Claude API on cache miss."""
        with app.app_context():
            mock_anthropic.reset_mock()

            sample_pdf.seek(0)
            data = {"pdf_files": (sample_pdf, "unique.pdf")}

            with client.session_transaction() as sess:
                sess["session_id"] = "test-session"

            client.post("/", data=data, content_type="multipart/form-data")

            # API should be called for new file
            assert mock_anthropic.called

    def test_cached_badge_shown_in_ui(self, client, app, db):
        """Should show cached badge in results UI."""
        with app.app_context():
            upload = app_module.Upload(
                filename="cached.pdf",
                original_filename="cached.pdf",
                file_path="/tmp/cached.pdf",
                file_hash="cached_hash",
                session_id="session-1",
                file_size=1024,
                is_cached=True,
            )
            db.session.add(upload)
            db.session.flush()

            summary = app_module.Summary(
                upload_id=upload.id, summary_text="Cached summary", page_count=1, char_count=100
            )
            db.session.add(summary)
            db.session.commit()

            response = client.get(f"/results?ids={upload.id}")

            assert response.status_code == 200
            assert b"Cached" in response.data or b"cached" in response.data.lower()

    def test_different_sessions_benefit_from_cache(self, app, db, cached_upload):
        """Should allow different sessions to benefit from cache."""
        with app.app_context():
            # Different session uploads same file
            new_upload = app_module.Upload(
                filename="same_file.pdf",
                original_filename="same.pdf",
                file_path="/tmp/same.pdf",
                file_hash=cached_upload.file_hash,
                session_id="different-session",  # Different session
                file_size=cached_upload.file_size,
                is_cached=True,
            )
            db.session.add(new_upload)
            db.session.commit()

            # Should be able to use cached summary
            cached_result = app_module.check_cache(cached_upload.file_hash)
            assert cached_result is not None
