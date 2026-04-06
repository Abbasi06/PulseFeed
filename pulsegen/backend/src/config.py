from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env paths: service dir first (pulsegen/backend/ locally, /app in Docker),
# then repo root (local dev only — Docker containers won't have a parent[3]).
_service_env = Path(__file__).parents[1] / ".env"
_parents = Path(__file__).parents
_root_env = (_parents[3] / ".env") if len(_parents) > 3 else _service_env


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_service_env, _root_env),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database & Storage ────────────────────────────────────────────────────
    storage_database_url: str = "postgresql://localhost/pulsegen"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── MCP server commands ───────────────────────────────────────────────────
    mcp_sql_command: str = "uv run python -m mcp_servers.sql_server"
    mcp_storage_command: str = "uv run python -m mcp_servers.storage_server"

    # ── Optional sources ─────────────────────────────────────────────────────
    github_token: str | None = None

    # ── llama.cpp servers (OpenAI-compatible, running natively on host) ───────
    # All servers run outside Docker so they have full system RAM with no container cap.
    # Light server (port 8080): gemma3-1b (~0.8 GB) — gatekeeper binary classification
    #   and validator scoring. Always on; negligible memory footprint.
    # Heavy server (port 8081): gemma4 (~9.4 GB) — extractor structured JSON extraction.
    #   Only under load during harvest windows (~10–20 min). llama.cpp mmap pages unused
    #   layers to disk so the full model loads without needing 9.4 GB hot in RAM.
    # Embedding server (port 8082): nomic-embed-text (~0.3 GB) — 768-dim vector search.
    llm_light_url: str = "http://host.docker.internal:8080/v1"
    llm_heavy_url: str = "http://host.docker.internal:8081/v1"
    llm_embed_url: str = "http://host.docker.internal:8082/v1"
    # llama.cpp accepts any non-empty string as the API key
    llm_api_key: str = "local"

    # ── Model names (informational — llama.cpp uses whatever GGUF is loaded) ──
    # Light tasks (gatekeeper, validator): simple classification/scoring → gemma3-1b
    # Heavy tasks (extractor): complex structured extraction → gemma4
    gatekeeper_model: str = "gemma3-1b"
    extractor_model: str = "gemma4"
    embedding_model: str = "nomic-embed-text"

    # ── Local state DB ────────────────────────────────────────────────────────
    generator_db_path: str = "generator.db"

    # ── Harvest tuning ────────────────────────────────────────────────────────
    harvest_target_per_source: int = 30
    gatekeeper_min_confidence: float = 0.6

    # ── Admin API ─────────────────────────────────────────────────────────────
    admin_api_port: int = 8001
    admin_api_key: str | None = None


settings = Settings()
