/*
 * Copyright 2025 Ilja Heitlager
 * SPDX-License-Identifier: Apache-2.0
 */

// Main JavaScript for PDF Summarizer

document.addEventListener('DOMContentLoaded', function() {
    console.log('PDF Summarizer loaded');

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-info)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // File size validation
    const fileInput = document.getElementById('pdf_files');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            validateFiles(this.files);
        });
    }

    // Form submission with loading state
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const files = fileInput.files;

            if (!files || files.length === 0) {
                e.preventDefault();
                alert('Please select at least one PDF file');
                return false;
            }

            // Show loading state
            const submitBtn = uploadForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
            }
        });
    }
});

// Validate file sizes and types
function validateFiles(files) {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const validTypes = ['application/pdf'];
    let hasError = false;

    for (let i = 0; i < files.length; i++) {
        const file = files[i];

        // Check file type
        if (!validTypes.includes(file.type) && !file.name.toLowerCase().endsWith('.pdf')) {
            alert(`Error: ${file.name} is not a PDF file`);
            hasError = true;
            break;
        }

        // Check file size
        if (file.size > maxSize) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            alert(`Error: ${file.name} is too large (${sizeMB} MB). Maximum size is 10 MB.`);
            hasError = true;
            break;
        }
    }

    if (hasError) {
        document.getElementById('pdf_files').value = '';
        document.getElementById('fileList').innerHTML = '';
    }

    return !hasError;
}

// Format file sizes
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Copy text to clipboard (fallback for older browsers)
function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            console.log('Text copied to clipboard');
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }
}
