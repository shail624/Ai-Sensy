# Backend production image (Doc 08 §6 — pinned, non-root, minimal).
# Multi-stage: build wheels, then a slim runtime. Targets Python 3.13.

# ---- Builder ----
FROM python:3.13-slim AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
# Install runtime dependencies into an isolated prefix for copying into the runtime.
RUN pip install --prefix=/install "fastapi>=0.115" "uvicorn[standard]>=0.32" \
    "pydantic>=2.9" "pydantic-settings>=2.5" "sqlalchemy[asyncio]>=2.0.35" \
    "alembic>=1.13" "asyncmy>=0.2.9" "redis>=5.0" "celery>=5.4" \
    "argon2-cffi>=23.1" "pyjwt>=2.9" "httpx>=0.27" "python-multipart>=0.0.12" \
    "email-validator>=2.2"

# ---- Runtime ----
FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000
# Non-root runtime user (Doc 08 §26 — least privilege / container hardening).
RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=app:app . /app
USER app
EXPOSE 8000
# Container-native liveness probe hitting the app's /health endpoint (Doc 04 §22).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
