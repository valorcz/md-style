# syntax=docker/dockerfile:1

# ==============================================================================
# Stage 1: viewer-builder
# Builds the Svelte 5 interactive viewer bundle and preps runtime node_modules
# ==============================================================================
FROM docker.io/library/node:22-bookworm-slim AS viewer-builder

WORKDIR /app/viewer

# Copy viewer dependencies and install
COPY viewer/package.json viewer/package-lock.json ./
RUN npm ci

# Copy viewer source files and configuration
COPY viewer/ ./
RUN mkdir -p /app/core/assets

# Recompile the interactive viewer bundle into /app/core/assets/
RUN npm run build

# Prune devDependencies to keep only runtime dependencies (pele, svelte)
RUN npm prune --omit=dev


# ==============================================================================
# Stage 2: python-builder
# Resolves and installs pure-Python dependencies into an isolated virtualenv
# ==============================================================================
FROM docker.io/library/python:3.12-slim-bookworm AS python-builder

# Install uv for fast and reproducible dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy Python project definition and install dependencies in editable mode
COPY pyproject.toml uv.lock README.md ./
COPY core/ core/
COPY styles/ styles/
COPY data/ data/
COPY static/ static/

RUN uv pip install --no-cache -e .


# ==============================================================================
# Stage 3: runtime-base
# Shared lightweight runtime containing Python venv, Node.js, and md-style assets
# ==============================================================================
FROM docker.io/library/python:3.12-slim-bookworm AS runtime-base

# Copy Node.js binary from builder (Node 22 with native WebSocket for CDP & pele)
COPY --from=viewer-builder /usr/local/bin/node /usr/local/bin/node

# Copy Python virtual environment
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/mdstyle \
    XDG_CACHE_HOME=/home/mdstyle/.cache

# Create non-root mdstyle user and establish permissive cache for rootless Podman
RUN groupadd -g 1000 mdstyle && \
    useradd -u 1000 -g mdstyle -m -d /home/mdstyle -s /bin/bash mdstyle && \
    mkdir -p /workspace /home/mdstyle/.cache /app && \
    chown -R mdstyle:mdstyle /home/mdstyle /workspace /app && \
    chmod -R 777 /home/mdstyle/.cache

WORKDIR /app

# Copy application directories maintaining layout relative to core/
COPY --chown=mdstyle:mdstyle pyproject.toml README.md ./
COPY --chown=mdstyle:mdstyle core/ core/
COPY --chown=mdstyle:mdstyle --from=viewer-builder /app/core/assets/ core/assets/
COPY --chown=mdstyle:mdstyle styles/ styles/
COPY --chown=mdstyle:mdstyle data/ data/
COPY --chown=mdstyle:mdstyle static/ static/
COPY --chown=mdstyle:mdstyle viewer/scripts/ viewer/scripts/
COPY --chown=mdstyle:mdstyle viewer/package.json viewer/
COPY --chown=mdstyle:mdstyle --from=viewer-builder /app/viewer/node_modules/ viewer/node_modules/

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /workspace
VOLUME ["/workspace"]
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]


# ==============================================================================
# Stage 4: slim target
# Minimal image without Chromium: suitable for HTML, Markdown, and RO-Crate export
# ==============================================================================
FROM runtime-base AS slim

USER mdstyle
CMD ["--help"]


# ==============================================================================
# Stage 5: full target (default)
# Full publication-grade document generator with Chromium CDP PDF printing
# ==============================================================================
FROM runtime-base AS full

# Install Chromium and core font packages for pixel-perfect PDF rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        chromium \
        fontconfig \
        fonts-liberation \
        fonts-dejavu-core && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/*

ENV CHROME_BIN=/usr/bin/chromium

USER mdstyle
CMD ["--help"]
