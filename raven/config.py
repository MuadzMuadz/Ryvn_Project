import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# LLM — chat model (OpenAI-compatible: LiteLLM proxy, LM Studio, Ollama, ...).
# Single shared endpoint, no fallback — points at the ryvn-litellm proxy.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# Per-request timeout (seconds). With no fallback, give the model room to finish a
# long generation instead of failing fast.
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))

# Firecrawl
FIRECRAWL_API_URL = os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "fc-local")

# Embeddings. Use their own endpoint (defaulting to the chat LLM's) because the
# Qdrant collection is bound to one model/dimension — keep this pinned to a stable
# endpoint and never change the model without re-indexing.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", OPENAI_BASE_URL)
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", OPENAI_API_KEY)

# Vector store — Qdrant (ryvn-qdrant). Use ":memory:" for tests/ephemeral runs.
# The collection is created lazily on first write using the embedding dimension.
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "raven_docs")

# File system
WATCH_PATHS = [
    p.strip() for p in os.getenv("WATCH_PATHS", str(Path.home())).split(",") if p.strip()
]
INDEXED_EXTENSIONS = set(
    os.getenv("INDEXED_EXTENSIONS", ".txt,.md,.pdf,.docx,.py,.js,.ts,.json,.csv").split(",")
)
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
INDEXED_DIR = DATA_DIR / "indexed"

# LangGraph checkpointer. Set DATABASE_URL to a Postgres DSN (ryvn-postgres) to
# persist conversation state in the stack; leave empty to use the local SQLite file.
DATABASE_URL = os.getenv("DATABASE_URL", "")
SESSIONS_DB = DATA_DIR / "sessions.db"

# Where the agent writes its own notes (the `save_note` tool). Defaults to a folder
# under data/; point it at your Obsidian vault to keep notes there, e.g.
#   NOTES_DIR=/mnt/c/Users/LEGION/Documents/Raven-Vault/Notes
NOTES_DIR = Path(os.getenv("NOTES_DIR", str(DATA_DIR / "notes"))).expanduser()

# Server
PORT = int(os.getenv("PORT", "1802"))

# API security
API_KEY = os.getenv("API_KEY", "").strip()
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Context window
MAX_CONVERSATION_TOKENS = int(os.getenv("MAX_CONVERSATION_TOKENS", "8000"))

# RAG retrieval
RAG_N_RESULTS = int(os.getenv("RAG_N_RESULTS", "5"))
# Max chars of retrieved-document context injected into the prompt, to keep requests
# within the model's context length (~4 chars/token). Default fits a 4096-token model;
# raise it once your LM Studio model is loaded with a larger context window.
RAG_CONTEXT_CHAR_BUDGET = int(os.getenv("RAG_CONTEXT_CHAR_BUDGET", "6000"))


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


# Auto-indexing daemon
# ENABLE_WATCHER: start the realtime filesystem watcher on startup. OFF by default:
#   inotify cannot watch /mnt/* (Windows drvfs), and recursively watching a huge tree
#   like all of $HOME blocks startup and floods on dotfile/app-state churn. Prefer a
#   focused WATCHER_PATHS (a documents folder) or the periodic index timer instead.
# WATCHER_PATHS: realtime-watch scope (comma-separated). Falls back to WATCH_PATHS.
# INDEX_ON_STARTUP: also run a one-time full index of WATCH_PATHS on startup (heavy).
ENABLE_WATCHER = _flag("ENABLE_WATCHER", "false")
WATCHER_PATHS = [
    p.strip() for p in os.getenv("WATCHER_PATHS", ",".join(WATCH_PATHS)).split(",") if p.strip()
]
INDEX_ON_STARTUP = _flag("INDEX_ON_STARTUP", "false")
