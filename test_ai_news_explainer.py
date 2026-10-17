import asyncio

from app.config import settings
from app.services import ai_news_explainer as service


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "INTINYA: contoh penjelasan."}}]}


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
    monkeypatch.setattr(settings, "huggingface_token", "test-secret")
    monkeypatch.setattr(settings, "ai_model", "Qwen/Qwen2.5-7B-Instruct")
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
    assert request["url"] == "https://router.huggingface.co/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-secret"
    assert request["json"]["model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert "Bahasa Indonesia" in request["json"]["messages"][0]["content"]
    assert "Tariff dispute escalates" in request["json"]["messages"][1]["content"]


def test_ai_explainer_requires_huggingface_token(monkeypatch):
    monkeypatch.setattr(settings, "huggingface_token", "")
    try:
        asyncio.run(service.explain_news_with_ai("Headline", "Source", "", None))
    except RuntimeError as exc:
        assert str(exc) == "AI_NOT_CONFIGURED"
    else:
        raise AssertionError("Expected missing token to stop the request")
