# =============================================================================
# REALITY.EXE Backend Dockerfile
#
# Multi-stage build:
#   builder  — installs all dependencies (including dev) in a disposable layer
#   runtime  — slim production image, non-root user, no build tools
#
# Build targets:
#   docker build --target runtime .        # production image (default)
#   docker build --target development .    # development image (hot-reload)
#
# The development target is only used via docker-compose.override.yml.
# Never deploy the development target to production.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1 — builder
# Installs all Python dependencies into /opt/venv so they can be copied
# to the runtime stage without carrying along pip, setuptools, or build tools.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# System packages needed only to compile C-extensions (psycopg2, bcrypt, Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    libwebp-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

WORKDIR /build

# Copy dependency manifests first to maximise cache reuse
COPY pyproject.toml README.md ./

# Install production dependencies only
RUN pip install --no-cache-dir .


# ---------------------------------------------------------------------------
# Stage 2 — runtime (production)
# Minimal image: no build tools, no pip, non-root user.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    # Application defaults (all overridable via environment / .env)
    ENVIRONMENT=production \
    DEBUG=false \
    LOG_LEVEL=INFO \
    API_V1_STR=/api/v1 \
    PORT=8000

# Runtime-only system libraries (libpq for asyncpg, libjpeg/libwebp for Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    libwebp7 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid 1001 --no-create-home --shell /bin/false appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy application source
COPY app/         ./app/
COPY alembic/     ./alembic/
COPY alembic.ini  ./
COPY scripts/     ./scripts/

# Create evidence upload directory and set ownership
RUN mkdir -p /data/evidence && chown -R appuser:appgroup /app /data

USER appuser

EXPOSE 8000

# Health check — uses the unauthenticated /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/health | python3 -c \
        "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d['status'] in ('healthy','degraded') else 1)" \
    || exit 1

# Default: production server
# Workers = (2 × CPU_cores) + 1  — override with WORKERS env var
CMD ["sh", "-c", \
     "python scripts/startup_check.py && \
      uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers ${WORKERS:-2}"]


# ---------------------------------------------------------------------------
# Stage 3 — development
# Extends runtime with dev dependencies and hot-reload.
# Source code is mounted at runtime (not baked in) via docker-compose.override.yml.
# ---------------------------------------------------------------------------
FROM runtime AS development

USER root

# Install dev dependencies into the existing venv
COPY pyproject.toml README.md /tmp/
RUN pip install --no-cache-dir "/tmp/.[dev]"

# Switch back to non-root
USER appuser

ENV ENVIRONMENT=development \
    DEBUG=true \
    LOG_LEVEL=DEBUG

# Development: single worker, hot-reload enabled
CMD ["sh", "-c", \
     "python scripts/startup_check.py && \
      uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --reload"]
