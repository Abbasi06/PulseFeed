from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Required ──────────────────────────────────────────────────────────────
    gemini_api_key: str

    # ── Database & Storage ────────────────────────────────────────────────────
    storage_database_url: str = "postgresql://localhost/pulsegen"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── MCP server commands ───────────────────────────────────────────────────
    mcp_sql_command: str = "uv run mcp-sql-server"
    mcp_storage_command: str = "uv run mcp-storage-server"

    # ── Optional sources ─────────────────────────────────────────────────────
    github_token: str | None = None

    # ── Gemini models (always free-tier Flash) ────────────────────────────────
    gatekeeper_model: str = "gemini-2.0-flash"
    extractor_model: str = "gemini-2.0-flash"
    embedding_model: str = "models/gemini-embedding-001"

    # ── Local state DB ────────────────────────────────────────────────────────
    generator_db_path: str = "generator.db"

    # ── Harvest tuning ────────────────────────────────────────────────────────
    harvest_target_per_source: int = 30
    gatekeeper_min_confidence: float = 0.6

    # ── Admin API ─────────────────────────────────────────────────────────────
    admin_api_port: int = 8001


settings = Settings()
