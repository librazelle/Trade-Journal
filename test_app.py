import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "app.db"))
    monkeypatch.setattr(settings, "enable_worker", False)
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_dashboard_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Catat entry" in r.text
    assert "Berita relevan untuk" in r.text
    assert "NASDAQ100" in r.text
    assert "S&amp;P500" in r.text or "S&P500" in r.text
    assert "Cara baca berita" in r.text
    assert "Bahasa super gampang" in r.text
    assert "news-category-nav" in r.text
    assert "data-news-filter=\"inflation\"" in r.text
    assert "data-news-filter=\"jobs\"" in r.text
    assert "External Research" in r.text
    assert "data-clock-view=\"reminder\"" in r.text
    assert "Checklist sebelum entry" in r.text
    assert "account-profile-select" in r.text
    assert "data-journal-target=\"trade\"" in r.text
    assert "data-journal-target=\"history\"" in r.text
    assert "data-clock-view=\"asia\"" in r.text
    assert "data-clock-view=\"europe\"" in r.text
    assert "data-clock-view=\"newyork\"" in r.text


def test_create_and_view_trade(client):
    r = client.post(
        "/trades",
        data={
            "instrument": "xauusd",
            "direction": "long",
            "entry_price": "2650.5",
            "entry_time": "2026-10-16T14:30",
            "lot": "",
            "sl": "2640",
            "tp": "",
            "note": "tes",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    detail = client.get(r.headers["location"])
    assert detail.status_code == 200
    assert "XAUUSD" in detail.text
    assert "Kalender ekonomi saat entry" in detail.text
    assert "Replay Mode" in detail.text
    assert "urutan kejadian" in detail.text


def test_invalid_direction_rejected(client):
    r = client.post(
        "/trades",
        data={"direction": "sideways", "entry_price": "1", "entry_time": "2026-10-16T14:30"},
    )
    assert r.status_code == 400


def test_health(client):
    assert client.get("/health").json() == {"ok": True}



class _FakeMarketResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("upstream error", request=None, response=None)

    def json(self):
        return self._payload


class _FakeMarketClient:
    payload = None
    requested_params = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        type(self).requested_params = params
        return _FakeMarketResponse(type(self).payload)


def _market_chart_payload():
    return {
        "chart": {
            "result": [{
                "timestamp": [1792300000, 1792300300, 1792300600],
                "indicators": {"quote": [{
                    "open": [100, 101, None],
                    "high": [102, 103, 104],
                    "low": [99, 100, 102],
                    "close": [101, 102, 103],
                }]},
                "meta": {
                    "currency": "USD",
                    "exchangeTimezoneName": "America/New_York",
                    "currentTradingPeriod": {"regular": {"start": 1, "end": 2}},
                },
            }],
            "error": None,
        }
    }


def test_market_monitor_endpoint_is_removed(client):
    response = client.get("/api/market-monitor/NASDAQ100?interval=5m")
    assert response.status_code == 404


def test_coinglass_endpoint_explains_missing_api_key(client, monkeypatch):
    monkeypatch.setattr(settings, "coinglass_api_key", "")
    response = client.get("/api/news-liquidity/coinglass?symbol=BTC&interval=5m")

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False
    assert "COINGLASS_API_KEY" in data["message"]
    assert data["liquidations"] == []
    assert data["open_interest"] == []


class _FakeMyfxbookResponse:
    status_code = 200
    text = """
    <h1>XAUUSD Forex Sentiment</h1>
    <p>55% of the forex traders are currently going short with XAU/USD, with an average price of 4183.4765, meanwhile 45% of the forex traders are going long with XAU/USD, with an average price of 4565.3927.</p>
    <table><tr><td>XAUUSD</td><td>short</td><td>55 %</td><td>898.32 lots</td><td>5,368</td><td>Long</td><td>45 %</td><td>881.77 lots</td><td>8,030</td></tr></table>
    """
    def raise_for_status(self):
        return None


class _FakeMyfxbookClient:
    def __init__(self, *args, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False
    async def get(self, url):
        return _FakeMyfxbookResponse()


def test_myfxbook_outlook_parses_public_sentiment(client, monkeypatch):
    from app import main
    main._MYFXBOOK_OUTLOOK_CACHE.clear()
    monkeypatch.setattr(main.httpx, "AsyncClient", _FakeMyfxbookClient)
    response = client.get("/api/myfxbook/outlook/XAUUSD")

    assert response.status_code == 200
    data = response.json()
    assert data["short_percentage"] == 55
    assert data["long_percentage"] == 45
    assert data["short_average_price"] == 4183.4765
    assert data["long_average_price"] == 4565.3927
    assert data["source_delay_minutes"] == 60


def test_myfxbook_outlook_rejects_other_symbol(client):
    response = client.get("/api/myfxbook/outlook/EURUSD")
    assert response.status_code == 400


def test_myfxbook_gemini_summary_requires_api_key(client, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    response = client.post("/api/myfxbook/outlook/summarize", json={
        "symbol": "XAUUSD", "short_percentage": 55, "long_percentage": 45
    })

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_news_liquidity_page_renders(client):
    response = client.get("/news-liquidity")
    assert response.status_code == 200
    assert "News Liquidity Lab" in response.text
    assert "Waktu rilis (WIB)" in response.text
    assert "Liquidity sweep check" in response.text
    assert "bukan bukti resting orders" in response.text
    assert "nl-csv-file" in response.text
    assert "nl-mf-load" in response.text
    assert "Ringkas dengan Gemini" in response.text
    assert "import CSV" in response.text or "import candle CSV" in response.text
