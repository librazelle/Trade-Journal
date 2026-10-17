import asyncio

from app.config import settings
from app.services import ai_news_explainer as service


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": "INTINYA: contoh penjelasan."}]}}]}


class FakeAsyncClient:
    last_request = None

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers, json):
        self.__class__.last_request = {"url": url, "headers": headers, "json": json}
        return FakeResponse()


def test_ai_explainer_sends_beginner_prompt_and_returns_text(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-secret")
    monkeypatch.setattr(settings, "gemini_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(service.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(
        service.explain_news_with_ai(
            title="Tariff dispute escalates",
            source="BBC News · World",
            summary="Leaders discuss trade policy.",
            url="https://example.test/story/1",
        )
    )

    assert result == "INTINYA: contoh penjelasan."
    request = FakeAsyncClient.last_request
    assert request["url"].endswith("/models/gemini-3.5-flash-lite:generateContent")
    assert request["headers"]["x-goog-api-key"] == "test-secret"
    assert "Bahasa Indonesia" in request["json"]["systemInstruction"]["parts"][0]["text"]
    assert "Tariff dispute escalates" in request["json"]["contents"][0]["parts"][0]["text"]


def test_ai_explainer_requires_gemini_api_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    try:
        asyncio.run(service.explain_news_with_ai("Headline", "Source", "", None))
    except RuntimeError as exc:
        assert str(exc) == "AI_NOT_CONFIGURED"
    else:
        raise AssertionError("Expected missing API key to stop the request")
