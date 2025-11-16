import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField
from wtforms.validators import ValidationError
from werkzeug.utils import secure_filename
from pypdf import PdfReader
from anthropic import Anthropic
from dotenv import load_dotenv
import io

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pdf_summaries.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


# Database Models
class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    summaries = db.relationship('Summary', backref='upload', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Upload {self.original_filename}>'


class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('upload.id'), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    page_count = db.Column(db.Integer)
    char_count = db.Column(db.Integer)

    def __repr__(self):
        return f'<Summary for Upload {self.upload_id}>'


# Flask-WTF Form
class UploadForm(FlaskForm):
    pdf_files = FileField(
        'PDF Files',
        validators=[
            FileRequired(),
            FileAllowed(['pdf'], 'Only PDF files are allowed!')
        ]
    )
    submit = SubmitField('Upload and Summarize')

    def validate_pdf_files(self, field):
        """Additional validation for file size"""
        if field.data:
            # Check file size (werkzeug FileStorage object)
            field.data.seek(0, 2)  # Seek to end
            file_size = field.data.tell()
            field.data.seek(0)  # Reset to beginning

            if file_size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError('File size must not exceed 10MB')


# Helper Functions
def extract_text_from_pdf(file_path):
    """Extract text from PDF file using pypdf"""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text, len(reader.pages)
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")


def summarize_with_claude(text):
    """Summarize text using Anthropic Claude API"""
    try:
        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"Please provide a concise summary of the following document. Focus on the main points, key findings, and important details:\n\n{text[:100000]}"  # Limit to ~100k chars to avoid token limits
                }
            ]
        )
        return message.content[0].text
    except Exception as e:
        raise Exception(f"Error with Claude API: {str(e)}")


def save_uploaded_file(file):
    """Save uploaded file with secure filename"""
    original_filename = file.filename
    filename = secure_filename(original_filename)

    # Add timestamp to avoid filename collisions
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{timestamp}{ext}"

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)

    # Get file size
    file_size = os.path.getsize(file_path)

    return file_path, unique_filename, original_filename, file_size


# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    form = UploadForm()

    if form.validate_on_submit():
        try:
            # Get uploaded files (multiple files support)
            files = request.files.getlist('pdf_files')

            if not files or files[0].filename == '':
                flash('No files selected', 'error')
                return redirect(request.url)

            processed_ids = []

            for file in files:
                # Validate file extension
                if not file.filename.lower().endswith('.pdf'):
                    flash(f'Skipped {file.filename}: Only PDF files are allowed', 'warning')
                    continue

                # Save the file
                file_path, unique_filename, original_filename, file_size = save_uploaded_file(file)

                # Create upload record
                upload = Upload(
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_size=file_size
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
                    char_count=len(text)
                )
                db.session.add(summary)

                processed_ids.append(upload.id)

            # Commit all changes
            db.session.commit()

            flash(f'Successfully processed {len(processed_ids)} file(s)', 'success')
            return redirect(url_for('results', ids=','.join(map(str, processed_ids))))

        except Exception as e:
            db.session.rollback()
            flash(f'Error processing files: {str(e)}', 'error')
            return redirect(request.url)

    # Get recent uploads for display
    recent_uploads = Upload.query.order_by(Upload.upload_date.desc()).limit(10).all()

    return render_template('index.html', form=form, recent_uploads=recent_uploads)


@app.route('/results')
def results():
    """Display results for uploaded PDFs"""
    ids = request.args.get('ids', '')

    if not ids:
        flash('No results to display', 'warning')
        return redirect(url_for('index'))

    try:
        upload_ids = [int(id) for id in ids.split(',')]
        uploads = Upload.query.filter(Upload.id.in_(upload_ids)).all()

        return render_template('results.html', uploads=uploads)
    except Exception as e:
        flash(f'Error loading results: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/download/<int:summary_id>')
def download_summary(summary_id):
    """Download summary as text file"""
    try:
        summary = Summary.query.get_or_404(summary_id)
        upload = summary.upload

        # Create text file in memory
        text_content = f"Summary of: {upload.original_filename}\n"
        text_content += f"Generated: {summary.created_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
        text_content += f"Pages: {summary.page_count}\n"
        text_content += f"Original document characters: {summary.char_count:,}\n"
        text_content += "\n" + "="*80 + "\n\n"
        text_content += summary.summary_text

        # Create BytesIO object
        buffer = io.BytesIO()
        buffer.write(text_content.encode('utf-8'))
        buffer.seek(0)

        # Generate download filename
        download_name = f"summary_{upload.original_filename.rsplit('.', 1)[0]}.txt"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=download_name,
            mimetype='text/plain'
        )
    except Exception as e:
        flash(f'Error downloading summary: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/all-summaries')
def all_summaries():
    """View all summaries"""
    uploads = Upload.query.order_by(Upload.upload_date.desc()).all()
    return render_template('results.html', uploads=uploads)


# Create database tables
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)
