# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Tests for session management functionality.
"""

from pdf_summarizer import main as app_module
from tests import _create_sample_pdf


class TestSessionManagement:
    """Tests for session ID creation and management."""

    def test_session_persists_across_requests(self, client, app):
        """Should maintain same session ID across multiple requests."""
        with app.app_context():
            # First request
            client.get("/")
            with client.session_transaction() as sess:
                session_id_1 = sess.get("session_id")

            # Second request
            client.get("/")
            with client.session_transaction() as sess:
                session_id_2 = sess.get("session_id")

            assert session_id_1 == session_id_2

    def test_different_clients_get_different_sessions(self, app):
        """Should assign different session IDs to different clients."""
        with app.app_context():
            client1 = app.test_client()
            client2 = app.test_client()

            client1.get("/")
            client2.get("/")

            with client1.session_transaction() as sess1:
                session_id_1 = sess1.get("session_id")

            with client2.session_transaction() as sess2:
                session_id_2 = sess2.get("session_id")

            assert session_id_1 != session_id_2

    def test_session_isolation(self, client, app, db, mock_anthropic):
        """Should isolate uploads between different sessions."""
        with app.app_context():
            # Client 1 uploads
            pdf1 = _create_sample_pdf()
            client.post(
                "/",
                data={"pdf_files": (pdf1, "client1.pdf")},
                content_type="multipart/form-data",
            )

            with client.session_transaction() as sess:
                session_1 = sess["session_id"]

            # Get uploads for session 1
            uploads_1 = app_module.Upload.query.filter_by(session_id=session_1).all()

            # Client 2
            client2 = app.test_client()
            client2_limiter = app_module.limiter
            client2_limiter.enabled = False

            pdf2 = _create_sample_pdf()
            client2.post(
                "/",
                data={"pdf_files": (pdf2, "client2.pdf")},
                content_type="multipart/form-data",
            )

            with client2.session_transaction() as sess:
                session_2 = sess["session_id"]

            uploads_2 = app_module.Upload.query.filter_by(session_id=session_2).all()

            # Sessions should be different
            assert session_1 != session_2
            # Each should have their own uploads
            assert len(uploads_1) == 1
            assert len(uploads_2) == 1
            assert uploads_1[0].original_filename == "client1.pdf"
            assert uploads_2[0].original_filename == "client2.pdf"
