import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_settings(**overrides) -> Settings:
    base = {"OPENAI_API_KEY": None, "OPENROUTER_API_KEY": None, "AI_MODEL_PROFILES": ""}
    return Settings(_env_file=None, **{**base, **overrides})


def test_production_refuses_the_default_secret_key():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make_settings(ENVIRONMENT="production", SECRET_KEY="change-me")
    assert make_settings(ENVIRONMENT="production", SECRET_KEY="a-long-random-production-value").SECRET_KEY


@pytest.mark.parametrize(
    "url",
    [
        "postgres://u:p@ep-x.neon.tech/db?sslmode=require",
        "postgresql://u:p@ep-x.neon.tech/db?sslmode=require",
        "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require",
    ],
)
def test_postgres_urls_use_the_installed_psycopg3_driver(url):
    assert make_settings(DATABASE_URL=url).DATABASE_URL == "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require"


def test_sqlite_url_is_left_alone():
    assert make_settings(DATABASE_URL="sqlite:///./dev.db").DATABASE_URL == "sqlite:///./dev.db"


def test_render_public_url_fills_in_the_backend_base_url(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://interviewai-api.onrender.com/")
    assert make_settings().OAUTH_REDIRECT_BASE_URL == "https://interviewai-api.onrender.com"
    explicit = make_settings(OAUTH_REDIRECT_BASE_URL="https://api.example.com")
    assert explicit.OAUTH_REDIRECT_BASE_URL == "https://api.example.com"


def test_no_keys_means_no_profiles():
    assert make_settings().ai_model_profiles == []


def test_openrouter_models_become_ordered_profiles_ahead_of_openai():
    settings = make_settings(
        OPENAI_API_KEY="sk-openai",
        OPENROUTER_API_KEY="sk-or",
        OPENROUTER_MODELS="google/gemma-4-31b-it:free, openrouter/free",
    )
    profiles = settings.ai_model_profiles

    assert [p["id"] for p in profiles] == [
        "openrouter:google/gemma-4-31b-it:free",
        "openrouter:openrouter/free",
        "default",
    ]
    gemma = profiles[0]
    assert gemma["base_url"] == "https://openrouter.ai/api/v1"
    assert gemma["api_key"] == "sk-or"
    # On OpenRouter the conversation model handles the webcam/screen snapshots itself.
    assert gemma["vision_model"] == "google/gemma-4-31b-it:free"
    assert gemma["label"] == "OpenRouter - google/gemma-4-31b-it (free)"
    assert profiles[1]["label"] == "OpenRouter - any free model"


def test_openai_profile_keeps_its_dedicated_vision_model():
    settings = make_settings(OPENAI_API_KEY="sk-openai", OPENAI_MODEL="gpt-4.1-mini", OPENAI_VISION_MODEL="gpt-4o-mini")
    (profile,) = settings.ai_model_profiles
    assert profile["model"] == "gpt-4.1-mini"
    assert profile["vision_model"] == "gpt-4o-mini"


def test_openai_vision_model_does_not_leak_onto_other_gateways():
    settings = make_settings(
        AI_MODEL_PROFILES='[{"id": "local", "model": "llama3", "api_key": "x", "base_url": "http://localhost:11434/v1"}]'
    )
    (profile,) = settings.ai_model_profiles
    assert profile["vision_model"] == "llama3"
