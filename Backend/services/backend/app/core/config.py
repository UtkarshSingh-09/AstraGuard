from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AstraGuard Backend"
    app_env: str = Field(default="dev")
    app_debug: bool = Field(default=True)

    mongodb_uri: str = Field(default="")
    mongodb_db_name: str = Field(default="astraguard")
    mongodb_atlas_required: bool = Field(default=True)

    redis_url: str = Field(default="")
    jobs_ttl_seconds: int = Field(default=1800)
    cas_provider_enabled: bool = Field(default=False)
    cas_provider_name: str = Field(default="cas_provider")
    cas_provider_base_url: str = Field(default="")
    cas_provider_api_key: str = Field(default="")
    groq_api_key: str = Field(default="")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    groq_timeout_seconds: int = Field(default=20)

    sebi_disclaimer: str = Field(
        default=(
            "AI-generated guidance for educational purposes only. "
            "Not licensed financial advice under SEBI IA Regulations."
        )
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
