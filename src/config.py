import os

# Ollama Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "naturalsql")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "8192"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))

# PostgreSQL Configuration
PG_HOST = os.getenv("PGHOST", "localhost")
PG_PORT = int(os.getenv("PGPORT", "5432"))
PG_USER = os.getenv("PGUSER", "postgres")
PG_PASSWORD = os.getenv("PGPASSWORD", "")
PG_DATABASE = os.getenv("PGDATABASE", "postgres")

# Compiler Guardrail Defaults
DEFAULT_LIMIT = 50
MAX_SURGICAL_RETRIES = 2
