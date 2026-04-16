#!/bin/bash
cd "$(dirname "$0")"

export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export HF_HUB_VERBOSITY=error
export TRANSFORMERS_VERBOSITY=error
export TOKENIZERS_PARALLELISM=false

uv run uvicorn raven.api.app:app --host 0.0.0.0 --port 1802 --reload --reload-exclude "data/*" --log-level info
