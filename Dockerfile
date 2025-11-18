# Copyright 2025 Ilja Heitlager
# SPDX-License-Identifier: Apache-2.0

# Accept platform arguments from buildx
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# ===================================
# Base Stage
# ===================================
FROM python:3.13-slim AS base

# Platform-specific optimizations
ARG TARGETPLATFORM
RUN case "${TARGETPLATFORM}" in \
    "linux/amd64") \
        echo "Building for AMD64 (AWS Fargate compatible)" \
        ;; \
    "linux/arm64") \
        echo "Building for ARM64 (M1/M2 Mac and AWS Graviton compatible)" \
        ;; \
    *) \
        echo "Building for platform: ${TARGETPLATFORM}" \
        ;; \
    esac

# ===================================
# Builder Stage
# ===================================
FROM base AS builder

# Set working directory
WORKDIR /app

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files and source code first (for layer caching)
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY main.py ./

# Install dependencies using uv
# --system flag installs to system Python (no venv needed in container)
RUN uv pip install --system -e .

# ===================================
# Runtime Stage
# ===================================
FROM base AS runtime

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY main.py ./

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app/data/db /app/uploads /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Create directories with proper permissions
RUN mkdir -p /app/data/db /app/uploads /app/logs

# Expose Flask port
EXPOSE 8000

# Environment variables (can be overridden)
ENV FLASK_HOST=0.0.0.0 \
    FLASK_PORT=8000 \
    DATABASE_URL=sqlite:////app/data/db/pdf_summaries.db \
    UPLOAD_FOLDER=/app/uploads \
    LOG_DIR=/app/logs \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "main"]
