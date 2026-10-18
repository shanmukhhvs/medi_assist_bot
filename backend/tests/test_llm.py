import pytest

from app.config import settings
from app.RAG import llm


@pytest.fixture
def no_providers(monkeypatch):
    for key in ("ONEMIN_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setattr(settings, key, "")
        monkeypatch.delenv(key, raising=False)


def test_no_provider_raises_clear_error(no_providers):
    with pytest.raises(llm.LLMUnavailableError) as exc:
        llm.call_llm("SQL Query: how many escalated claims?")
    assert "No LLM provider" in str(exc.value)


def test_all_providers_failing_raises(monkeypatch, no_providers):
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "x")

    def boom(*a, **k):
        raise RuntimeError("quota exceeded")
    monkeypatch.setattr(llm, "_call_gemini", boom)
    with pytest.raises(llm.LLMUnavailableError) as exc:
        llm.call_llm("hi")
    assert "gemini" in str(exc.value).lower()


def test_no_canned_fallback_left():
    assert not hasattr(llm, "_fallback_synthesizer")
