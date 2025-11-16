"""
Shared test fixtures and configuration for pytest.

This module provides fixtures for:
- Flask application with test configuration
- Database with fresh schema
- HTTP test client
- Mock external dependencies (Anthropic API, file system)
- Sample data generators
"""

import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pdf_summarizer import main as app_module


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    # Create temporary directories for testing
    temp_dir = tempfile.mkdtemp()
    upload_dir = os.path.join(temp_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # Configure app for testing
    app_module.app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # In-memory database
            "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
            "UPLOAD_FOLDER": upload_dir,
            "SECRET_KEY": "test-secret-key",
            "SERVER_NAME": "localhost.localdomain",
        }
    )

    # Create app context
    with app_module.app.app_context():
        app_module.db.create_all()
        yield app_module.app
        app_module.db.session.remove()
        app_module.db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the app with rate limiting disabled."""
    # Disable rate limiter for tests
    app_module.limiter.enabled = False
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def db(app):
    """Return the database instance."""
    return app_module.db


@pytest.fixture(autouse=True)
def reset_database(db, app):
    """Reset database before each test."""
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        yield db
        db.session.remove()


@pytest.fixture
def mock_anthropic(mocker):
    """Mock Anthropic API client."""
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a test summary of the document.")]

    mock_create = mocker.patch.object(
        app_module.anthropic_client.messages, "create", return_value=mock_response
    )

    return mock_create


@pytest.fixture
def mock_claude_response():
    """Return mock Claude API response data."""
    return {
        "text": "This is a test summary of the document.",
        "model": "claude-3-5-sonnet-20241022",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


@pytest.fixture
def sample_pdf():
    """Generate a simple PDF file in memory."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Test PDF Document")
    c.drawString(100, 730, "This is a sample PDF file for testing.")
    c.drawString(100, 710, "It contains multiple lines of text.")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def _create_sample_pdf():
    """Helper function to create a fresh sample PDF."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Test PDF Document")
    c.drawString(100, 730, "This is a sample PDF file for testing.")
    c.drawString(100, 710, "It contains multiple lines of text.")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


@pytest.fixture
def multipage_pdf():
    """Generate a multi-page PDF file in memory."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Page 1
    c.drawString(100, 750, "Page 1")
    c.drawString(100, 730, "This is the first page.")
    c.showPage()

    # Page 2
    c.drawString(100, 750, "Page 2")
    c.drawString(100, 730, "This is the second page.")
    c.showPage()

    # Page 3
    c.drawString(100, 750, "Page 3")
    c.drawString(100, 730, "This is the third page.")
    c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


@pytest.fixture
def empty_pdf():
    """Generate an empty PDF file in memory."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


@pytest.fixture
def corrupted_pdf():
    """Generate a corrupted PDF file."""
    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\nCorrupted content that is not a valid PDF\n%%EOF")
    buffer.seek(0)
    return buffer


@pytest.fixture
def large_pdf():
    """Generate a large PDF file (>10MB) for size validation testing."""
    buffer = BytesIO()
    # Write 11MB of data
    buffer.write(b"%PDF-1.4\n")
    buffer.write(b"x" * (11 * 1024 * 1024))
    buffer.write(b"\n%%EOF")
    buffer.seek(0)
    return buffer


@pytest.fixture
def sample_upload(db, app):
    """Create a sample Upload record in the database."""
    with app.app_context():
        upload = app_module.Upload(
            filename="test_20231116_120000.pdf",
            original_filename="test.pdf",
            file_path="/tmp/uploads/test_20231116_120000.pdf",
            file_hash="abc123def456",
            session_id="test-session-id",
            file_size=1024,
            is_cached=False,
        )
        db.session.add(upload)
        db.session.commit()
        upload_id = upload.id
        db.session.expunge_all()

    # Return a fresh instance that can be used in tests
    with app.app_context():
        return db.session.get(app_module.Upload, upload_id)


@pytest.fixture
def sample_summary(db, app, sample_upload):
    """Create a sample Summary record in the database."""
    with app.app_context():
        summary = app_module.Summary(
            upload_id=sample_upload.id,
            summary_text="This is a test summary.",
            page_count=1,
            char_count=100,
        )
        db.session.add(summary)
        db.session.commit()
        summary_id = summary.id
        db.session.expunge_all()

    # Return a fresh instance that can be used in tests
    with app.app_context():
        return db.session.get(app_module.Summary, summary_id)


@pytest.fixture
def cached_upload(db, app):
    """Create a cached Upload with Summary for cache testing."""
    with app.app_context():
        upload = app_module.Upload(
            filename="cached_20231116_120000.pdf",
            original_filename="cached.pdf",
            file_path="/tmp/uploads/cached_20231116_120000.pdf",
            file_hash="cached_hash_123",
            session_id="session-1",
            file_size=2048,
            is_cached=False,
        )
        db.session.add(upload)
        db.session.flush()

        summary = app_module.Summary(
            upload_id=upload.id, summary_text="Cached summary text.", page_count=2, char_count=200
        )
        db.session.add(summary)
        db.session.commit()
        db.session.refresh(upload)
        return upload


@pytest.fixture
def mock_session_id():
    """Return a consistent mock session ID."""
    return "12345678-1234-1234-1234-123456789abc"


@pytest.fixture
def temp_upload_dir(tmp_path):
    """Create a temporary upload directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir


@pytest.fixture(autouse=True)
def mock_upload_folder(mocker, tmp_path):
    """Mock the upload folder to use tmp_path."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(exist_ok=True)
    mocker.patch.object(
        app_module.app.config,
        "__getitem__",
        side_effect=lambda k: (
            str(upload_dir) if k == "UPLOAD_FOLDER" else app_module.app.config.data.get(k)
        ),
    )
    return upload_dir


@pytest.fixture
def mock_logger(mocker):
    """Mock the application logger."""
    return mocker.patch.object(app_module.app, "logger")


@pytest.fixture
def mock_api_logger(mocker):
    """Mock the API logger."""
    return mocker.patch.object(app_module, "api_logger")


@pytest.fixture(autouse=True)
def disable_scheduler(mocker):
    """Disable the background scheduler for tests."""
    mocker.patch.object(app_module.scheduler, "start")
    mocker.patch.object(app_module.scheduler, "shutdown")


@pytest.fixture
def mock_cleanup_job(mocker):
    """Mock the cleanup job function."""
    return mocker.patch.object(app_module, "cleanup_old_uploads")
