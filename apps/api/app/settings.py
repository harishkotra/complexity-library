from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets are never included in public responses or logs."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"
    analysis_confidence_threshold: float = Field(default=0.85, ge=0, le=1)
    max_code_characters: int = Field(default=20_000, ge=100, le=200_000)
    llm_enabled: bool = False
    llm_provider: str = "openai"
    llm_model: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    redis_url: str = "redis://localhost:6379/0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def safe_runtime_summary(self) -> dict[str, str | bool | int | float]:
        return {
            "app_env": self.app_env,
            "llm_enabled": self.llm_enabled,
            "llm_provider": self.llm_provider if self.llm_enabled else "disabled",
            "analysis_confidence_threshold": self.analysis_confidence_threshold,
            "max_code_characters": self.max_code_characters,
            "supabase_configured": bool(self.supabase_url),
            "redis_configured": bool(self.redis_url),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
