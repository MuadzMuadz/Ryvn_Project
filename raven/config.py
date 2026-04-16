import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# LLM (OpenAI-compatible: works with LiteLLM proxy, Ollama, etc.)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)  # e.g. http://***REMOVED***:4000/v1
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Firecrawl
FIRECRAWL_API_URL = os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "fc-local")

# Embeddings & Vector Store
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
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
