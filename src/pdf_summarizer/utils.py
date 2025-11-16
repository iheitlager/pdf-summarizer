# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

import hashlib
import os
from datetime import datetime

from pypdf import PdfReader
from werkzeug.utils import secure_filename


def calculate_file_hash(file_path):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def extract_text_from_pdf(file_path, logger=None):
    """Extract text from PDF file using pypdf"""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text, len(reader.pages)
    except Exception as e:
        if logger:
            logger.error(f"PDF extraction failed for {file_path}: {str(e)}")
        raise Exception(f"Error reading PDF: {str(e)}") from e


def save_uploaded_file(file, upload_folder):
    """Save uploaded file with secure filename"""
    original_filename = file.filename
    filename = secure_filename(original_filename)

    # Add timestamp to avoid filename collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{timestamp}{ext}"

    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    # Get file size
    file_size = os.path.getsize(file_path)

    return file_path, unique_filename, original_filename, file_size
