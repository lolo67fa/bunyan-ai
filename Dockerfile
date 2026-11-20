# BUNYAN AI: one image for the whole app (club demo and cloud).
#   - the React frontend, built for production and served by the backend (one origin)
#   - the FastAPI backend and the five Python agents (BA direct backend, no CrewAI)
#   - Node.js and Playwright Chromium for the real QA Tester
# Runs as a non-root user; projects and generated files live in /data (mount a volume).

# ---------- 1. frontend build ----------
FROM node:22-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Same origin as the API: requests go to /projects/... on the page's own host.
ENV VITE_API_MODE=http VITE_API_BASE_URL=""
RUN npm run build

# ---------- 2. runtime ----------
FROM python:3.11-slim-bookworm AS runtime

# Node.js 22 for the QA suite (copied from the official image, no apt repository needed)
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    NPM_CONFIG_UPDATE_NOTIFIER=false

WORKDIR /app

# Python: FastAPI + the Business Analyst's direct Anthropic backend (no CrewAI, no dev tools)
COPY backend/agents/business_analyst/requirements.txt backend/agents/business_analyst/requirements-direct.txt /tmp/req/
RUN pip install "fastapi>=0.110,<1" "uvicorn>=0.29,<1" -r /tmp/req/requirements-direct.txt && rm -rf /tmp/req

# QA suite dependencies and Chromium with its system libraries
COPY tests/e2e/package.json tests/e2e/package-lock.json tests/e2e/
RUN cd tests/e2e && npm ci --no-audit --no-fund \
 && npx playwright install --with-deps chromium \
 && rm -rf /root/.npm /var/lib/apt/lists/*

# Application code (see .dockerignore) and the built frontend
COPY backend/ backend/
COPY templates/ templates/
COPY tests/e2e/ tests/e2e/
COPY docker/entrypoint.sh /usr/local/bin/bunyan-entrypoint
COPY --from=frontend /src/frontend/dist /app/frontend-dist

# Non-root user. It owns only what it must write: /data and the QA report folder.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin bunyan \
 && mkdir -p /data tests/e2e/reports \
 && chown -R bunyan:bunyan /data tests/e2e/reports \
 && chmod 0755 /usr/local/bin/bunyan-entrypoint

ENV BUNYAN_DATA_DIR=/data \
    BUNYAN_FRONTEND_DIR=/app/frontend-dist \
    BUNYAN_AUTH=required \
    BA_MODE=mock \
    PORT=8000

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=4)" || exit 1

# The entrypoint fixes /data ownership when a platform mounts the volume as root,
# then drops to the bunyan user before starting the server.
ENTRYPOINT ["bunyan-entrypoint"]
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
