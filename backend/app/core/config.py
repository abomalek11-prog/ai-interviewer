from functools import cached_property
import json
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "AI Interviewer"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_interviewer"
    SECRET_KEY: str = Field(default="change-me", min_length=8)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    FRONTEND_BASE_URL: str = "http://localhost:5173"
    OAUTH_REDIRECT_BASE_URL: str = "http://localhost:8000"

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None

    X_CLIENT_ID: str | None = None
    X_CLIENT_SECRET: str | None = None

    APPLE_CLIENT_ID: str | None = None
    APPLE_TEAM_ID: str | None = None
    APPLE_KEY_ID: str | None = None
    APPLE_PRIVATE_KEY: str | None = None

    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_MODEL_PROFILE_ID: str = "default"
    AI_MODEL_PROFILES: str = ""
    AI_FALLBACK_ENABLED: bool = True
    OPENAI_TTS_MODEL: str = "tts-1"
    OPENAI_TTS_VOICE: str = "alloy"
    OPENAI_VISION_MODEL: str = "gpt-4o-mini"

    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "no-reply@interviewai.app"

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @cached_property
    def ai_model_profiles(self) -> list[dict[str, str | None]]:
        """Configured AI model profiles without exposing secrets to the frontend.

        AI_MODEL_PROFILES supports either JSON or semicolon-separated records:
        id|label|model|api_key_env;premium|Premium|gpt-4.1|OPENAI_API_KEY_PREMIUM
        """
        profiles: list[dict[str, str | None]] = []

        if self.AI_MODEL_PROFILES.strip():
            try:
                raw_profiles = json.loads(self.AI_MODEL_PROFILES)
                for item in raw_profiles:
                    api_key = item.get("api_key") or os.getenv(item.get("api_key_env", ""))
                    profiles.append(
                        {
                            "id": item["id"],
                            "label": item.get("label") or item["id"],
                            "model": item["model"],
                            "api_key": api_key,
                            "base_url": item.get("base_url") or self.OPENAI_BASE_URL,
                        }
                    )
            except json.JSONDecodeError:
                for record in self.AI_MODEL_PROFILES.split(";"):
                    parts = [part.strip() for part in record.split("|")]
                    if len(parts) != 4 or not parts[0]:
                        continue
                    profile_id, label, model, api_key_env = parts
                    profiles.append(
                        {
                            "id": profile_id,
                            "label": label or profile_id,
                            "model": model,
                            "api_key": os.getenv(api_key_env),
                            "base_url": self.OPENAI_BASE_URL,
                        }
                    )

        if self.OPENAI_API_KEY:
            profiles.insert(
                0,
                {
                    "id": self.OPENAI_MODEL_PROFILE_ID,
                    "label": "Default OpenAI",
                    "model": self.OPENAI_MODEL,
                    "api_key": self.OPENAI_API_KEY,
                    "base_url": self.OPENAI_BASE_URL,
                },
            )

        deduped: dict[str, dict[str, str | None]] = {}
        for profile in profiles:
            deduped[profile["id"] or "default"] = profile
        return list(deduped.values())


settings = Settings()
