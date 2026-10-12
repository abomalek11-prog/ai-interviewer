from functools import cached_property
import json
import os

from pydantic import Field, field_validator, model_validator
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

    # OpenRouter (OpenAI-compatible gateway). Each model in OPENROUTER_MODELS becomes its own
    # profile, tried in order, so a rate-limited free model falls through to the next one.
    # `openrouter/free` is OpenRouter's router over whatever free models are currently live.
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODELS: str = "nvidia/nemotron-3-ultra-550b-a55b:free,nvidia/nemotron-3-super-120b-a12b:free,openrouter/free"

    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "no-reply@interviewai.app"

    @field_validator("DATABASE_URL")
    @classmethod
    def _use_psycopg3_driver(cls, url: str) -> str:
        # Hosts (Neon, Render, Heroku) hand out postgres:// or postgresql:// URLs, which
        # SQLAlchemy maps to psycopg2 - not installed here. Point them at psycopg 3.
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @model_validator(mode="after")
    def _public_url_from_host(self) -> "Settings":
        # Render publishes the service's own https URL; use it for avatar links and OAuth
        # callbacks unless OAUTH_REDIRECT_BASE_URL was set explicitly.
        render_url = os.getenv("RENDER_EXTERNAL_URL")
        if render_url and "OAUTH_REDIRECT_BASE_URL" not in self.model_fields_set:
            self.OAUTH_REDIRECT_BASE_URL = render_url.rstrip("/")
        return self

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        # Anyone who knows the default key can mint valid login tokens for any user.
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == "change-me":
            raise ValueError("SECRET_KEY must be set to a long random value when ENVIRONMENT=production")
        return self

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

        def vision_model_for(model: str, base_url: str | None) -> str:
            # OPENAI_VISION_MODEL names an OpenAI model, so it only applies on OpenAI's own
            # endpoint; on any other gateway the profile's model handles the snapshots too.
            if not base_url or "openai.com" in base_url:
                return self.OPENAI_VISION_MODEL
            return model

        if self.AI_MODEL_PROFILES.strip():
            try:
                raw_profiles = json.loads(self.AI_MODEL_PROFILES)
                for item in raw_profiles:
                    api_key = item.get("api_key") or os.getenv(item.get("api_key_env", ""))
                    base_url = item.get("base_url") or self.OPENAI_BASE_URL
                    profiles.append(
                        {
                            "id": item["id"],
                            "label": item.get("label") or item["id"],
                            "model": item["model"],
                            "vision_model": item.get("vision_model") or vision_model_for(item["model"], base_url),
                            "api_key": api_key,
                            "base_url": base_url,
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
                            "vision_model": vision_model_for(model, self.OPENAI_BASE_URL),
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
                    "vision_model": vision_model_for(self.OPENAI_MODEL, self.OPENAI_BASE_URL),
                    "api_key": self.OPENAI_API_KEY,
                    "base_url": self.OPENAI_BASE_URL,
                },
            )

        # Inserted ahead of OpenAI: when an OpenRouter key is present it is the intended
        # (free) provider, and OpenAI only serves as the paid fallback behind it.
        if self.OPENROUTER_API_KEY:
            models = [m.strip() for m in self.OPENROUTER_MODELS.split(",") if m.strip()]
            profiles[:0] = [
                {
                    "id": f"openrouter:{model}",
                    "label": (
                        "OpenRouter - any free model"
                        if model == "openrouter/free"
                        else f"OpenRouter - {model.removesuffix(':free')}" + (" (free)" if model.endswith(":free") else "")
                    ),
                    "model": model,
                    "vision_model": model,
                    "api_key": self.OPENROUTER_API_KEY,
                    "base_url": self.OPENROUTER_BASE_URL,
                }
                for model in models
            ]

        deduped: dict[str, dict[str, str | None]] = {}
        for profile in profiles:
            deduped[profile["id"] or "default"] = profile
        return list(deduped.values())


settings = Settings()
