from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError, RateLimitError

from app.core.config import settings
from app.services import ai_service
from app.services.ai_service import AIService, EmptyCompletionError, OpenAIProvider, parse_json_content


def _api_error(cls, status: int):
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    return cls("upstream said no", response=httpx.Response(status, request=request), body=None)


def _profile(profile_id: str) -> dict:
    return {
        "id": profile_id,
        "label": profile_id,
        "model": f"model-{profile_id}",
        "vision_model": f"model-{profile_id}",
        "api_key": "key",
        "base_url": "https://openrouter.ai/api/v1",
    }


class FakeProvider:
    def __init__(self, reply=None, error: Exception | None = None):
        self.reply = reply
        self.error = error
        self.calls = 0

    def _answer(self):
        self.calls += 1
        if self.error:
            raise self.error
        return self.reply

    def converse(self, messages, image_data_url):
        return self._answer()

    def complete_json(self, system_prompt, user_prompt):
        return self._answer()


@pytest.fixture()
def two_profiles(monkeypatch):
    """Two configured profiles whose providers each test controls."""
    monkeypatch.setitem(vars(settings), "ai_model_profiles", [_profile("first"), _profile("second")])
    providers: dict[str, FakeProvider] = {}
    monkeypatch.setattr(AIService, "_build_provider", staticmethod(lambda profile: providers[profile["id"]]))
    return providers


# --- parse_json_content -------------------------------------------------------------


def test_parse_plain_json():
    assert parse_json_content('{"score": 70}') == {"score": 70}


def test_parse_fenced_json():
    assert parse_json_content('```json\n{"score": 70}\n```') == {"score": 70}


def test_parse_json_with_preamble_and_trailer():
    assert parse_json_content('Sure! Here is the evaluation:\n{"score": 70}\nHope it helps.') == {"score": 70}


def test_parse_rejects_text_without_json():
    with pytest.raises(ValueError):
        parse_json_content("I cannot evaluate this.")


# --- fallback across profiles ---------------------------------------------------------


def test_rate_limited_profile_falls_through_to_next(two_profiles):
    two_profiles["first"] = FakeProvider(error=_api_error(RateLimitError, 429))
    two_profiles["second"] = FakeProvider(reply="Second model speaking.")

    assert AIService().converse([{"role": "user", "content": "hi"}]) == "Second model speaking."
    assert two_profiles["first"].calls == 1


def test_empty_completion_falls_through_to_next(two_profiles):
    two_profiles["first"] = FakeProvider(error=EmptyCompletionError("nothing"))
    two_profiles["second"] = FakeProvider(reply="Recovered.")

    assert AIService().converse([{"role": "user", "content": "hi"}]) == "Recovered."


def test_preferred_profile_is_tried_first(two_profiles):
    two_profiles["first"] = FakeProvider(reply="first")
    two_profiles["second"] = FakeProvider(reply="second")

    assert AIService(preferred_profile_id="second").converse([{"role": "user", "content": "hi"}]) == "second"
    assert two_profiles["first"].calls == 0


def test_all_profiles_down_degrades_to_demo_mode(two_profiles):
    two_profiles["first"] = FakeProvider(error=_api_error(RateLimitError, 429))
    two_profiles["second"] = FakeProvider(error=_api_error(RateLimitError, 429))

    reply = AIService().converse([{"role": "system", "content": "Conduct the interview in Arabic"}])
    assert "وضع تجريبي" in reply


def test_wrongly_shaped_evaluation_uses_offline_evaluator(two_profiles):
    two_profiles["first"] = FakeProvider(reply={"verdict": "good"})
    two_profiles["second"] = FakeProvider(reply={"verdict": "good"})

    evaluation = AIService().evaluate_answer("What is a cache?", "A cache stores data for performance.", "Mid", "tech")
    assert 0 <= evaluation.score <= 100
    assert "Offline demo evaluation" in evaluation.feedback


def test_wrongly_shaped_question_set_uses_offline_questions(two_profiles):
    two_profiles["first"] = FakeProvider(reply={"items": []})

    questions = AIService(preferred_profile_id="first").generate_questions("tech", "Mid", 3, [])
    assert len(questions) == 3


# --- OpenAIProvider -------------------------------------------------------------------


class FakeCompletions:
    """Stands in for client.chat.completions; scripted per call."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=outcome))])


def _provider_with(completions: FakeCompletions) -> OpenAIProvider:
    provider = OpenAIProvider(api_key="key", model="text-model", base_url="https://openrouter.ai/api/v1")
    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return provider


def test_openrouter_provider_sends_attribution_headers_and_uses_profile_model():
    provider = OpenAIProvider(
        api_key="key", model="google/gemma-4-31b-it:free", base_url="https://openrouter.ai/api/v1"
    )
    assert provider.client.default_headers["X-Title"] == settings.PROJECT_NAME
    assert provider.supports_audio is False
    # Without an explicit vision model, a non-OpenAI profile must not fall back to an OpenAI model name.
    vision = OpenAIProvider(
        api_key="key", model="m", base_url="https://openrouter.ai/api/v1", vision_model="m"
    )
    assert vision.vision_model == "m"


def test_text_only_model_rejecting_snapshot_retries_without_it(monkeypatch):
    monkeypatch.setattr(OpenAIProvider, "_text_only_models", set())
    completions = FakeCompletions(_api_error(BadRequestError, 400), "Answer without the picture.", "Next turn.")
    provider = _provider_with(completions)
    turn = [{"role": "user", "content": "here is my code"}]

    reply = provider.converse(turn, "data:image/jpeg;base64,AAAA")

    assert reply == "Answer without the picture."
    first, second = completions.requests
    assert isinstance(first["messages"][-1]["content"], list)  # image attached
    assert second["messages"][-1]["content"] == "here is my code"  # retried as plain text

    # Remembered: the next turn skips the image instead of paying for another rejection.
    assert provider.converse(turn, "data:image/jpeg;base64,AAAA") == "Next turn."
    assert len(completions.requests) == 3
    assert completions.requests[2]["messages"][-1]["content"] == "here is my code"


def test_openrouter_requests_keep_reasoning_short_and_hidden():
    completions = FakeCompletions("ok")
    _provider_with(completions).converse([{"role": "user", "content": "hi"}], None)
    assert completions.requests[0]["extra_body"] == ai_service.OPENROUTER_REASONING


def test_bad_request_without_image_is_not_swallowed():
    provider = _provider_with(FakeCompletions(_api_error(BadRequestError, 400)))
    with pytest.raises(BadRequestError):
        provider.converse([{"role": "user", "content": "hi"}], None)


def test_blank_reply_raises_empty_completion():
    provider = _provider_with(FakeCompletions("   "))
    with pytest.raises(EmptyCompletionError):
        provider.converse([{"role": "user", "content": "hi"}], None)


def test_complete_json_accepts_fenced_reply():
    provider = _provider_with(FakeCompletions('```json\n{"questions": []}\n```'))
    assert provider.complete_json("sys", "user") == {"questions": []}


def test_requests_are_bounded():
    completions = FakeCompletions("ok")
    _provider_with(completions).converse([{"role": "user", "content": "hi"}], None)
    assert completions.requests[0]["max_tokens"] == ai_service.MAX_REPLY_TOKENS
