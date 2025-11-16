# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

import atexit
import hashlib
import io
import os
import time
import uuid
from datetime import UTC, datetime, timedelta

from anthropic import Anthropic
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from pypdf import PdfReader
from werkzeug.utils import secure_filename
from wtforms import SubmitField
from wtforms.validators import ValidationError

# Import logging configuration
from .logging_config import (
    log_api_call,
    log_cache_hit,
    log_cache_miss,
    log_cleanup,
    log_error_with_context,
    log_processing,
    log_rate_limit,
    log_upload,
    setup_logging,
)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pdf_summaries.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB max file size
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

# Ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use Redis in production: os.getenv('REDIS_URL', 'redis://localhost:6379')
)

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Setup logging
api_logger = setup_logging(app)


# Database Models
class Upload(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_hash = db.Column(
        db.String(64), index=True
    )  # SHA256 hash for caching (not unique - multiple uploads can share hash)
    session_id = db.Column(db.String(255), index=True)  # Track user sessions
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    file_size = db.Column(db.Integer)
    is_cached = db.Column(db.Boolean, default=False)  # Whether this was a cache hit
    summaries = db.relationship(
        "Summary", backref="upload", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Upload {self.original_filename}>"


class Summary(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("upload.id"), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    page_count = db.Column(db.Integer)
    char_count = db.Column(db.Integer)

    def __repr__(self):
        return f"<Summary for Upload {self.upload_id}>"


# Flask-WTF Form
class UploadForm(FlaskForm):
    pdf_files = FileField(
        "PDF Files",
        validators=[FileRequired(), FileAllowed(["pdf"], "Only PDF files are allowed!")],
    )
    submit = SubmitField("Upload and Summarize")

    def validate_pdf_files(self, field):
        """Additional validation for file size"""
        if field.data:
            # Check file size (werkzeug FileStorage object)
            field.data.seek(0, 2)  # Seek to end
            file_size = field.data.tell()
            field.data.seek(0)  # Reset to beginning

            if file_size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError("File size must not exceed 10MB")


# Helper Functions
def get_or_create_session_id():
    """Get or create a unique session ID for the user"""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        session.permanent = True
        app.logger.info(f"New session created: {session['session_id'][:8]}...")
    return session["session_id"]


def calculate_file_hash(file_path):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def check_cache(file_hash):
    """Check if a file with this hash has been processed before"""
    cached_upload = Upload.query.filter_by(file_hash=file_hash).first()
    if cached_upload and cached_upload.summaries:
        return cached_upload
    return None


def extract_text_from_pdf(file_path):
    """Extract text from PDF file using pypdf"""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text, len(reader.pages)
    except Exception as e:
        app.logger.error(f"PDF extraction failed for {file_path}: {str(e)}")
        raise Exception(f"Error reading PDF: {str(e)}") from e


def validate_claude_model():
    """Validate that the configured Claude model is available"""
    model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    try:
        # Make a minimal test call to validate the model exists
        anthropic_client.messages.create(
            model=model,
            max_tokens=10,
            messages=[
                {
                    "role": "user",
                    "content": "test",
                }
            ],
        )
        app.logger.info(f"✓ Claude model '{model}' is available and accessible")
        return True
    except Exception as e:
        app.logger.error(f"✗ Claude model '{model}' validation failed: {str(e)}")
        app.logger.warning(
            "Please check your CLAUDE_MODEL environment variable or verify your API key"
        )
        return False


def summarize_with_claude(text):
    """Summarize text using Anthropic Claude API"""
    start_time = time.time()
    try:
        # Use Claude model (configurable via environment variable)
        model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        message = anthropic_client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"Please provide a concise summary of the following document. Focus on the main points, key findings, and important details:\n\n{text[:100000]}",  # Limit to ~100k chars to avoid token limits
                }
            ],
        )
        duration = time.time() - start_time
        log_api_call(api_logger, "Claude Summarization", duration, success=True)
        # Extract text content from response, filtering for TextBlock types only
        for block in message.content:
            if hasattr(block, "text"):
                return block.text
        raise Exception("No text content in Claude response")
    except Exception as e:
        duration = time.time() - start_time
        log_api_call(api_logger, "Claude Summarization", duration, success=False, error=str(e))
        app.logger.error(f"Claude API error: {str(e)}")
        raise Exception(f"Error with Claude API: {str(e)}") from e


def save_uploaded_file(file):
    """Save uploaded file with secure filename"""
    original_filename = file.filename
    filename = secure_filename(original_filename)

    # Add timestamp to avoid filename collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{timestamp}{ext}"

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    file.save(file_path)

    # Get file size
    file_size = os.path.getsize(file_path)

    return file_path, unique_filename, original_filename, file_size


def cleanup_old_uploads():
    """Delete uploads older than retention period"""
    try:
        retention_days = int(os.getenv("RETENTION_DAYS", "30"))
        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        old_uploads = Upload.query.filter(Upload.upload_date < cutoff_date).all()

        deleted_count = 0
        freed_space = 0

        for upload in old_uploads:
            # Delete file from disk
            if os.path.exists(upload.file_path):
                file_size = os.path.getsize(upload.file_path)
                os.remove(upload.file_path)
                freed_space += file_size
                app.logger.info(f"Deleted file: {upload.file_path}")

            # Delete from database (cascades to summaries)
            db.session.delete(upload)
            deleted_count += 1

        db.session.commit()

        freed_space_mb = freed_space / (1024 * 1024)
        log_cleanup(app.logger, deleted_count, freed_space_mb)
        app.logger.info(f"Cleanup completed: {deleted_count} files, {freed_space_mb:.2f} MB freed")

    except Exception as e:
        db.session.rollback()
        log_error_with_context(app.logger, e, "Cleanup job")


# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    app.logger.warning(f"404 error: {request.url}")
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f"500 error: {str(error)}", exc_info=True)
    return render_template("errors/500.html"), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    log_rate_limit(app.logger, get_remote_address(), request.endpoint)
    return render_template("errors/429.html"), 429


# Routes
@app.route("/", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def index():
    form = UploadForm()
    session_id = get_or_create_session_id()

    if form.validate_on_submit():
        start_time = time.time()
        try:
            # Get uploaded files (multiple files support)
            files = request.files.getlist("pdf_files")

            if not files or files[0].filename == "":
                flash("No files selected", "error")
                return redirect(request.url)

            processed_ids = []
            cached_count = 0

            for file in files:
                # Validate file extension
                if not file.filename or not file.filename.lower().endswith(".pdf"):
                    flash(f"Skipped {file.filename}: Only PDF files are allowed", "warning")
                    continue

                # Save the file
                file_path, unique_filename, original_filename, file_size = save_uploaded_file(file)
                log_upload(app.logger, original_filename, file_size, session_id)

                # Calculate file hash for caching
                file_hash = calculate_file_hash(file_path)

                # Check cache
                cached_upload = check_cache(file_hash)

                if cached_upload:
                    # Cache hit - create new upload record pointing to cached summary
                    log_cache_hit(app.logger, file_hash)

                    upload = Upload(
                        filename=unique_filename,
                        original_filename=original_filename,
                        file_path=file_path,
                        file_hash=file_hash,
                        session_id=session_id,
                        file_size=file_size,
                        is_cached=True,
                    )
                    db.session.add(upload)
                    db.session.flush()

                    # Copy summary from cached upload
                    cached_summary = cached_upload.summaries[0]
                    summary = Summary(
                        upload_id=upload.id,
                        summary_text=cached_summary.summary_text,
                        page_count=cached_summary.page_count,
                        char_count=cached_summary.char_count,
                    )
                    db.session.add(summary)
                    cached_count += 1

                else:
                    # Cache miss - process the file
                    log_cache_miss(app.logger, file_hash)

                    # Create upload record
                    upload = Upload(
                        filename=unique_filename,
                        original_filename=original_filename,
                        file_path=file_path,
                        file_hash=file_hash,
                        session_id=session_id,
                        file_size=file_size,
                        is_cached=False,
                    )
                    db.session.add(upload)
                    db.session.flush()  # Get the ID without committing

                    # Extract text from PDF
                    text, page_count = extract_text_from_pdf(file_path)

                    # Generate summary with Claude
                    summary_text = summarize_with_claude(text)

                    # Create summary record
                    summary = Summary(
                        upload_id=upload.id,
                        summary_text=summary_text,
                        page_count=page_count,
                        char_count=len(text),
                    )
                    db.session.add(summary)

                    processing_time = time.time() - start_time
                    log_processing(
                        app.logger, original_filename, page_count, len(text), processing_time
                    )

                processed_ids.append(upload.id)

            # Commit all changes
            db.session.commit()

            success_msg = f"Successfully processed {len(processed_ids)} file(s)"
            if cached_count > 0:
                success_msg += f" ({cached_count} from cache)"
            flash(success_msg, "success")

            app.logger.info(
                f"Batch processing completed: {len(processed_ids)} files, {cached_count} cached"
            )
            return redirect(url_for("results", ids=",".join(map(str, processed_ids))))

        except Exception as e:
            db.session.rollback()
            log_error_with_context(app.logger, e, f"Upload processing for session {session_id[:8]}")
            flash(f"Error processing files: {str(e)}", "error")
            return redirect(request.url)

    # Get recent uploads for this session
    recent_uploads = (
        Upload.query.filter_by(session_id=session_id)
        .order_by(Upload.upload_date.desc())
        .limit(10)
        .all()
    )

    return render_template("index.html", form=form, recent_uploads=recent_uploads)


@app.route("/results")
def results():
    """Display results for uploaded PDFs"""
    ids = request.args.get("ids", "")

    if not ids:
        flash("No results to display", "warning")
        return redirect(url_for("index"))

    try:
        upload_ids = [int(id) for id in ids.split(",")]
        uploads = Upload.query.filter(Upload.id.in_(upload_ids)).all()

        app.logger.info(f"Displaying results for {len(uploads)} uploads")
        return render_template("results.html", uploads=uploads)
    except Exception as e:
        log_error_with_context(app.logger, e, f"Results display for IDs: {ids}")
        flash(f"Error loading results: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/download/<int:summary_id>")
def download_summary(summary_id):
    """Download summary as text file"""
    try:
        summary = db.session.get(Summary, summary_id)
        if not summary:
            abort(404)
        upload = summary.upload

        # Create text file in memory
        text_content = f"Summary of: {upload.original_filename}\n"
        text_content += f"Generated: {summary.created_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
        text_content += f"Pages: {summary.page_count}\n"
        text_content += f"Original document characters: {summary.char_count:,}\n"
        if upload.is_cached:
            text_content += "Source: Cached summary\n"
        text_content += "\n" + "=" * 80 + "\n\n"
        text_content += summary.summary_text

        # Create BytesIO object
        buffer = io.BytesIO()
        buffer.write(text_content.encode("utf-8"))
        buffer.seek(0)

        # Generate download filename
        download_name = f"summary_{upload.original_filename.rsplit('.', 1)[0]}.txt"

        app.logger.info(f"Summary downloaded: {download_name}")
        return send_file(
            buffer, as_attachment=True, download_name=download_name, mimetype="text/plain"
        )
    except Exception as e:
        log_error_with_context(app.logger, e, f"Download summary {summary_id}")
        flash(f"Error downloading summary: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/my-uploads")
def my_uploads():
    """View uploads for current session"""
    session_id = get_or_create_session_id()
    uploads = (
        Upload.query.filter_by(session_id=session_id).order_by(Upload.upload_date.desc()).all()
    )

    app.logger.info(f"My uploads accessed by session {session_id[:8]}: {len(uploads)} uploads")
    return render_template("results.html", uploads=uploads, title="My Uploads")


@app.route("/all-summaries")
def all_summaries():
    """View all summaries"""
    uploads = Upload.query.order_by(Upload.upload_date.desc()).all()
    app.logger.info(f"All summaries accessed: {len(uploads)} total uploads")
    return render_template("results.html", uploads=uploads, title="All Summaries")


# Scheduler for cleanup job
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=cleanup_old_uploads,
    trigger="cron",
    hour=int(os.getenv("CLEANUP_HOUR", "3")),  # Default: 3 AM
    minute=0,
)
scheduler.start()


# Create database tables
with app.app_context():
    db.create_all()
    # Validate Claude model availability
    if not validate_claude_model():
        app.logger.critical("Claude model validation failed - aborting application startup")
        raise RuntimeError(
            "Claude model is not available. Check CLAUDE_MODEL environment variable and API key"
        )


# Shutdown scheduler on app exit
atexit.register(lambda: scheduler.shutdown())


if __name__ == "__main__":
    app.run(debug=True)
