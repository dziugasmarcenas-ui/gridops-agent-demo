from pydantic import field_validator
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
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    # The hosted demo can require HTTP Basic Auth without putting credentials
    # in the frontend bundle. Local development remains open by default.
    require_demo_auth: bool = False
    demo_auth_username: str = "demo"
    demo_auth_password: str | None = None

    model_config = SettingsConfigDict(env_prefix="GRIDOPS_", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def use_installed_psycopg_driver(cls, value: str) -> str:
        # Render supplies PostgreSQL URLs without a SQLAlchemy driver suffix;
        # this project installs psycopg 3 rather than psycopg2.
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


settings = Settings()
