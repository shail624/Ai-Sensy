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
# `pyproject.toml` declares `readme = "README.md"`; setuptools resolves that path at build time, so
# the file must be present or the install aborts with a FileNotFoundError before a single
# dependency is fetched.
COPY pyproject.toml README.md ./
# Install from the project's own dependency definition, never a copy of it. A hand-maintained
# list silently omits anything added later (openpyxl for XLSX export, cryptography for token
# encryption, aiosqlite), producing an image that starts and then fails at the first export.
# Runtime extras stay out because only the base project is installed (dev dependencies live in
# the `dev` optional group).
COPY app ./app
RUN pip install --prefix=/install .

# ---- Runtime ----
FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000
# Non-root runtime user (Doc 08 §26 — least privilege / container hardening).
RUN groupadd --system app && useradd --system --gid app --home /app app

# Create the mount points **in the image**, owned by the runtime user.
#
# This is load-bearing, not tidiness. When Docker initialises an empty named volume it copies the
# ownership and mode of the image directory underneath it; if that directory does not exist, the
# volume is created root-owned and a non-root process cannot write to it. Without these two lines
# the stack starts and then fails in ways that look unrelated to the container user:
#   /var/lib/wa/media — every media download and every export write fails (and `/ready` still
#                       reports storage "up", because its probe is read-only)
#   /var/run/celery   — beat cannot write its schedule file and exits, so nothing periodic runs
RUN mkdir -p /var/lib/wa/media /var/run/celery \
    && chown -R app:app /var/lib/wa /var/run/celery

WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=app:app . /app
# Baked in, not bind-mounted: the image must be runnable on its own (`docker run <image> worker`),
# and a mounted entrypoint silently breaks when the host checkout has CRLF endings.
RUN cp /app/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh \
    && chmod 0755 /usr/local/bin/docker-entrypoint.sh

USER app
EXPOSE 8000
# Container-native liveness probe hitting the app's /health endpoint (Doc 04 §22).
# This matches the image's default role (`api`). The worker and beat roles serve no HTTP, so the
# Compose manifest overrides this with a role-appropriate probe — `celery inspect ping` for the
# pools, the schedule file for beat. `migrate` inherits it but exits before it matters.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"]
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["api"]
