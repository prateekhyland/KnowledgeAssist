"""Central configuration, loaded from environment / .env."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    # Server
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = _int("APP_PORT", 8000)
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    allowed_origins: list[str] = [
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
    ]
    app_name: str = os.getenv("APP_NAME", "KnowledgeAssist")

    # Database
    pg_host: str = os.getenv("PGHOST", "localhost")
    pg_port: int = _int("PGPORT", 5432)
    pg_database: str = os.getenv("PGDATABASE", "docs_bot")
    pg_user: str = os.getenv("PGUSER", "docs_bot")
    pg_password: str = os.getenv("PGPASSWORD", "")

    # Storage backend: "pgvector" (Postgres) or "local" (NumPy file, no server needed)
    vector_store: str = os.getenv("VECTOR_STORE", "pgvector")
    local_store_path: str = os.getenv("LOCAL_STORE_PATH", "data/index.pkl")

    # Embedding backend: "sentence_transformers" (local torch models) or "ollama"
    embed_backend: str = os.getenv("EMBED_BACKEND", "sentence_transformers")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    # Embeddings / reranker (sentence_transformers backend)
    embed_model: str = os.getenv("EMBED_MODEL", "BAAI/bge-large-en-v1.5")
    embed_dim: int = _int("EMBED_DIM", 1024)
    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    query_instruction: str = os.getenv(
        "QUERY_INSTRUCTION",
        "Represent this sentence for searching relevant passages:",
    )

    # LLM (Ollama)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")
    llm_temperature: float = _float("LLM_TEMPERATURE", 0.1)
    llm_num_ctx: int = _int("LLM_NUM_CTX", 8192)

    # Retrieval
    retrieve_top_k: int = _int("RETRIEVE_TOP_K", 20)
    rerank_top_n: int = _int("RERANK_TOP_N", 6)

    # Security / codegen demo
    enable_private_code_encryption: bool = _bool(
        "ENABLE_PRIVATE_CODE_ENCRYPTION", True
    )
    encryption_key_id: str = os.getenv("ENCRYPTION_KEY_ID", "demo-key")

    @property
    def pg_dsn(self) -> str:
        return (
            f"host={self.pg_host} port={self.pg_port} dbname={self.pg_database} "
            f"user={self.pg_user} password={self.pg_password}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
