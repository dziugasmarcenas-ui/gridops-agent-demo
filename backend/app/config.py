from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration lives here so nothing is hardcoded in business logic.

    Reads from environment variables first (see DATABASE_URL in
    docker-compose.yml), falling back to these defaults for local runs
    outside Docker.
    """

    database_url: str = "postgresql+psycopg://gridops:gridops@localhost:54329/gridops"

    # Optional: if unset, embeddings fall back to a deterministic local hash
    # (see embeddings.py) so RAG works with zero external configuration.
    voyage_api_key: str | None = None
    voyage_model: str = "voyage-3-lite"

    # Optional: if unset, the agent endpoint returns a clear error instead of
    # silently failing, rather than fabricating a response.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    model_config = SettingsConfigDict(env_prefix="GRIDOPS_", extra="ignore")


settings = Settings()
