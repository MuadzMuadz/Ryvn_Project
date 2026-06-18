# Raven backend — thin-client API server for the ryvn-* stack.
# Talks to ryvn-litellm (chat + embeddings) and ryvn-qdrant (vectors) over the
# shared Docker network; no local model/vector deps baked in.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first for better layer caching. Production only (--no-dev).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Application code (backend package + scripts). The web UI is a single static file
# served by the API itself, so no separate frontend build is needed.
COPY raven ./raven
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

EXPOSE 1802

CMD ["uv", "run", "uvicorn", "raven.api.app:app", "--host", "0.0.0.0", "--port", "1802"]
