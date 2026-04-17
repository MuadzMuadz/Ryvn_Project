#!/bin/bash
cd "$(dirname "$0")"

export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export HF_HUB_VERBOSITY=error
export TRANSFORMERS_VERBOSITY=error
export TOKENIZERS_PARALLELISM=false

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

PORT="${PORT:-1802}"

uv run uvicorn raven.api.app:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --reload \
  --reload-exclude "data/*" \
  --log-level info
