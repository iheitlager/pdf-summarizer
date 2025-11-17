# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

"""
Routes module.

This module contains all Flask route handlers and helper functions
for the PDF Summarizer application.
"""

import io
import time
import uuid

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from .claude_service import summarize_with_claude
from .extensions import db, limiter
from .forms import PromptTemplateForm, UploadForm
from .logging_config import (
    log_cache_hit,
    log_cache_miss,
    log_error_with_context,
    log_processing,
    log_upload,
)
from .models import PromptTemplate, Summary, Upload
from .utils import calculate_file_hash, extract_text_from_pdf, save_uploaded_file


def get_or_create_session_id():
    """
    Get or create a unique session ID for the user.

    Returns:
        str: Session ID (UUID)
    """
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        session.permanent = True
        current_app.logger.info(f"New session created: {session['session_id'][:8]}...")
    return session["session_id"]


def check_cache(file_hash, prompt_template_id=None):
    """
    Check if a file with this hash has been processed before with the same prompt.

    Args:
        file_hash: SHA256 hash of the file
        prompt_template_id: ID of the prompt template used (optional)

    Returns:
        Upload: Cached upload record if found, None otherwise
    """
    # Find uploads with matching file hash
    uploads = Upload.query.filter_by(file_hash=file_hash).all()

    # Check if any have a summary with matching prompt_template_id
    for upload in uploads:
        if upload.summaries:
            summary = upload.summaries[0]
            if summary.prompt_template_id == prompt_template_id:
                return upload

    return None


def register_routes(app):
    """
    Register all routes with the Flask application.

    Args:
        app: Flask application instance
    """

    @app.route("/", methods=["GET", "POST"])
    @limiter.limit("10 per hour")
    def index():
        """Main upload form and processing route."""
        form = UploadForm()
        session_id = get_or_create_session_id()

        # Populate prompt template choices
        active_prompts = PromptTemplate.query.filter_by(is_active=True).all()
        if not active_prompts:
            flash("No active prompt templates available. Please create one.", "error")
            return redirect(url_for("prompts_list"))

        form.prompt_template.choices = [(p.id, p.name) for p in active_prompts]

        # Set default to "Basic Summary" if available
        if request.method == "GET":
            default_prompt = next((p for p in active_prompts if p.name == "Basic Summary"), None)
            if default_prompt:
                form.prompt_template.data = default_prompt.id
            elif active_prompts:
                form.prompt_template.data = active_prompts[0].id

        if form.validate_on_submit():
            # Get selected prompt template
            prompt_template_id = form.prompt_template.data
            prompt_template = PromptTemplate.query.get(prompt_template_id)
            if not prompt_template:
                flash("Invalid prompt template selected", "error")
                return redirect(request.url)
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
                    file_path, unique_filename, original_filename, file_size = save_uploaded_file(
                        file, app.config["UPLOAD_FOLDER"]
                    )
                    log_upload(app.logger, original_filename, file_size, session_id)

                    # Calculate file hash for caching
                    file_hash = calculate_file_hash(file_path)

                    # Check cache (with prompt template)
                    cached_upload = check_cache(file_hash, prompt_template_id)

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
                            prompt_template_id=prompt_template_id,
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
                        text, page_count = extract_text_from_pdf(file_path, app.logger)

                        # Generate summary with Claude using selected prompt
                        summary_text = summarize_with_claude(
                            text, app.logger, prompt_text=prompt_template.prompt_text
                        )

                        # Create summary record
                        summary = Summary(
                            upload_id=upload.id,
                            prompt_template_id=prompt_template_id,
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
                log_error_with_context(
                    app.logger, e, f"Upload processing for session {session_id[:8]}"
                )
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
        """Display results for uploaded PDFs."""
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
        """Download summary as text file."""
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
        """View uploads for current session."""
        session_id = get_or_create_session_id()
        uploads = (
            Upload.query.filter_by(session_id=session_id).order_by(Upload.upload_date.desc()).all()
        )

        app.logger.info(f"My uploads accessed by session {session_id[:8]}: {len(uploads)} uploads")
        return render_template("results.html", uploads=uploads, title="My Uploads")

    @app.route("/all-summaries")
    def all_summaries():
        """View all summaries."""
        uploads = Upload.query.order_by(Upload.upload_date.desc()).all()
        app.logger.info(f"All summaries accessed: {len(uploads)} total uploads")
        return render_template("results.html", uploads=uploads, title="All Summaries")

    @app.route("/prompts")
    def prompts_list():
        """List all prompt templates."""
        prompts = PromptTemplate.query.order_by(PromptTemplate.created_date.desc()).all()
        app.logger.info(f"Prompts list accessed: {len(prompts)} templates")
        return render_template("prompts/list.html", prompts=prompts)

    @app.route("/prompts/new", methods=["GET", "POST"])
    def prompts_new():
        """Create a new prompt template."""
        form = PromptTemplateForm()

        if form.validate_on_submit():
            try:
                # Check if name already exists
                existing = PromptTemplate.query.filter_by(name=form.name.data).first()
                if existing:
                    flash(f"A prompt template with name '{form.name.data}' already exists", "error")
                    return redirect(request.url)

                prompt = PromptTemplate(
                    name=form.name.data,
                    prompt_text=form.prompt_text.data,
                    is_active=form.is_active.data,
                )
                prompt.validate()  # Run model validation
                db.session.add(prompt)
                db.session.commit()

                flash(f"Prompt template '{prompt.name}' created successfully", "success")
                app.logger.info(f"New prompt template created: {prompt.name}")
                return redirect(url_for("prompts_list"))

            except ValueError as e:
                flash(f"Validation error: {str(e)}", "error")
                return redirect(request.url)
            except Exception as e:
                db.session.rollback()
                log_error_with_context(app.logger, e, "Create prompt template")
                flash(f"Error creating prompt template: {str(e)}", "error")
                return redirect(request.url)

        return render_template("prompts/form.html", form=form, title="Create Prompt Template")

    @app.route("/prompts/<int:prompt_id>/edit", methods=["GET", "POST"])
    def prompts_edit(prompt_id):
        """Edit an existing prompt template."""
        prompt = PromptTemplate.query.get_or_404(prompt_id)
        form = PromptTemplateForm(obj=prompt)

        if form.validate_on_submit():
            try:
                # Check if name already exists (excluding current prompt)
                existing = PromptTemplate.query.filter(
                    PromptTemplate.name == form.name.data, PromptTemplate.id != prompt_id
                ).first()
                if existing:
                    flash(f"A prompt template with name '{form.name.data}' already exists", "error")
                    return redirect(request.url)

                prompt.name = form.name.data
                prompt.prompt_text = form.prompt_text.data
                prompt.is_active = form.is_active.data
                prompt.validate()  # Run model validation

                db.session.commit()

                flash(f"Prompt template '{prompt.name}' updated successfully", "success")
                app.logger.info(f"Prompt template updated: {prompt.name}")
                return redirect(url_for("prompts_list"))

            except ValueError as e:
                flash(f"Validation error: {str(e)}", "error")
                return redirect(request.url)
            except Exception as e:
                db.session.rollback()
                log_error_with_context(app.logger, e, f"Edit prompt template {prompt_id}")
                flash(f"Error updating prompt template: {str(e)}", "error")
                return redirect(request.url)

        return render_template(
            "prompts/form.html", form=form, title=f"Edit Prompt: {prompt.name}", prompt=prompt
        )

    @app.route("/prompts/<int:prompt_id>/delete", methods=["POST"])
    def prompts_delete(prompt_id):
        """Delete a prompt template."""
        prompt = PromptTemplate.query.get_or_404(prompt_id)

        try:
            # Check if prompt is in use by any summaries
            summary_count = Summary.query.filter_by(prompt_template_id=prompt_id).count()
            if summary_count > 0:
                flash(
                    f"Cannot delete prompt '{prompt.name}': it is used by {summary_count} summaries",
                    "error",
                )
                return redirect(url_for("prompts_list"))

            prompt_name = prompt.name
            db.session.delete(prompt)
            db.session.commit()

            flash(f"Prompt template '{prompt_name}' deleted successfully", "success")
            app.logger.info(f"Prompt template deleted: {prompt_name}")

        except Exception as e:
            db.session.rollback()
            log_error_with_context(app.logger, e, f"Delete prompt template {prompt_id}")
            flash(f"Error deleting prompt template: {str(e)}", "error")

        return redirect(url_for("prompts_list"))
