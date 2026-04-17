import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# LLM (OpenAI-compatible: works with LiteLLM proxy, Ollama, etc.)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Firecrawl
FIRECRAWL_API_URL = os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "fc-local")

# Embeddings & Vector Store
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "data" / "vectors"))
CHROMA_COLLECTION = "raven_docs"

# File system
WATCH_PATHS = [
    p.strip()
    for p in os.getenv("WATCH_PATHS", str(Path.home())).split(",")
    if p.strip()
]
INDEXED_EXTENSIONS = set(
    os.getenv("INDEXED_EXTENSIONS", ".txt,.md,.pdf,.docx,.py,.js,.ts,.json,.csv").split(",")
)
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
INDEXED_DIR = DATA_DIR / "indexed"
SESSIONS_DB = DATA_DIR / "sessions.db"

# Server
PORT = int(os.getenv("PORT", "1802"))

# API security
API_KEY = os.getenv("API_KEY", "").strip()
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

# Context window
MAX_CONVERSATION_TOKENS = int(os.getenv("MAX_CONVERSATION_TOKENS", "8000"))
