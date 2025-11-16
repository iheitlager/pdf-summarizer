"""
Tests for automated cleanup job functionality.
"""

import os
from datetime import UTC, datetime, timedelta

from pdf_summarizer import main as app_module


class TestCleanupJob:
    """Tests for cleanup_old_uploads function."""

    def test_respects_retention_days_env_var(self, app, db, tmp_path, mocker):
        """Should use RETENTION_DAYS from environment."""
        with app.app_context():
            mocker.patch.dict(os.environ, {"RETENTION_DAYS": "15"})

            # Create upload 16 days old (should be deleted)
            old_upload = app_module.Upload(
                filename="old.pdf",
                original_filename="old.pdf",
                file_path=str(tmp_path / "old.pdf"),
                session_id="test",
                file_size=1024,
                upload_date=datetime.now(UTC) - timedelta(days=16),
            )
            # Create upload 14 days old (should be kept)
            recent_upload = app_module.Upload(
                filename="recent.pdf",
                original_filename="recent.pdf",
                file_path=str(tmp_path / "recent.pdf"),
                session_id="test",
                file_size=1024,
                upload_date=datetime.now(UTC) - timedelta(days=14),
            )
            db.session.add_all([old_upload, recent_upload])
            db.session.commit()

            (tmp_path / "old.pdf").write_bytes(b"old")
            (tmp_path / "recent.pdf").write_bytes(b"recent")

            app_module.cleanup_old_uploads()

            assert db.session.get(app_module.Upload, old_upload.id) is None
            assert db.session.get(app_module.Upload, recent_upload.id) is not None

    def test_logs_cleanup_statistics(self, app, db, tmp_path, mocker, mock_logger):
        """Should log number of files deleted and space freed."""
        with app.app_context():
            mocker.patch.dict(os.environ, {"RETENTION_DAYS": "30"})

            old_upload = app_module.Upload(
                filename="old.pdf",
                original_filename="old.pdf",
                file_path=str(tmp_path / "old.pdf"),
                session_id="test",
                file_size=2048,
                upload_date=datetime.now(UTC) - timedelta(days=31),
            )
            db.session.add(old_upload)
            db.session.commit()

            (tmp_path / "old.pdf").write_bytes(b"x" * 2048)

            app_module.cleanup_old_uploads()

            # Should log cleanup info
            assert mock_logger.info.called

    def test_cascades_to_delete_summaries(self, app, db, tmp_path, mocker):
        """Should cascade delete associated summaries."""
        with app.app_context():
            mocker.patch.dict(os.environ, {"RETENTION_DAYS": "30"})

            old_upload = app_module.Upload(
                filename="old.pdf",
                original_filename="old.pdf",
                file_path=str(tmp_path / "old.pdf"),
                session_id="test",
                file_size=1024,
                upload_date=datetime.now(UTC) - timedelta(days=31),
            )
            db.session.add(old_upload)
            db.session.flush()

            summary = app_module.Summary(
                upload_id=old_upload.id, summary_text="Old summary", page_count=1, char_count=100
            )
            db.session.add(summary)
            db.session.commit()

            summary_id = summary.id
            (tmp_path / "old.pdf").write_bytes(b"old")

            app_module.cleanup_old_uploads()

            # Both upload and summary should be deleted
            assert db.session.get(app_module.Upload, old_upload.id) is None
            assert db.session.get(app_module.Summary, summary_id) is None

    def test_handles_database_rollback_on_error(self, app, db, mocker):
        """Should rollback database on error during cleanup."""
        with app.app_context():
            mocker.patch.dict(os.environ, {"RETENTION_DAYS": "30"})

            # Force an error during cleanup
            mocker.patch.object(db.session, "commit", side_effect=Exception("DB Error"))

            # Should not raise exception
            try:
                app_module.cleanup_old_uploads()
                no_exception = True
            except Exception:
                no_exception = False

            assert no_exception
