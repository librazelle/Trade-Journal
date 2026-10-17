import asyncio

from app.config import settings
from app.services import ai_news_explainer as service


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "INTINYA: contoh penjelasan."}
                    ],
                }
            ]
        }


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
    monkeypatch.setattr(settings, "openai_api_key", "test-secret")
    monkeypatch.setattr(settings, "ai_model", "gpt-6-luna")
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
    assert request["url"] == "https://api.openai.com/v1/responses"
    assert request["headers"]["Authorization"] == "Bearer test-secret"
    assert request["json"]["model"] == "gpt-6-luna"
    assert request["json"]["store"] is False
    assert "Bahasa Indonesia" in request["json"]["instructions"]
    assert "Tariff dispute escalates" in request["json"]["input"]


def test_ai_explainer_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    try:
        asyncio.run(service.explain_news_with_ai("Headline", "Source", "", None))
    except RuntimeError as exc:
        assert str(exc) == "AI_NOT_CONFIGURED"
    else:
        raise AssertionError("Expected missing API key to stop the request")
