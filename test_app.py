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
    assert "Berita berdampak tinggi" in r.text
    assert "NASDAQ100" in r.text
    assert "S&amp;P500" in r.text or "S&P500" in r.text
    assert "Cara baca berita" in r.text
    assert "Bahasa super gampang" in r.text
    assert "news-category-nav" in r.text
    assert "data-news-filter=\"inflation\"" in r.text
    assert "data-news-filter=\"jobs\"" in r.text
    assert "External Research" in r.text
    assert "data-clock-view=\"drawdown\"" in r.text
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


def test_market_monitor_returns_valid_candles(client, monkeypatch):
    from app import main

    _FakeMarketClient.payload = _market_chart_payload()
    monkeypatch.setattr(main.httpx, "AsyncClient", _FakeMarketClient)
    response = client.get("/api/market-monitor/NASDAQ100?interval=5m")

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "^NDX"
    assert data["status"] == "DELAY_UNKNOWN"
    assert len(data["candles"]) == 2
    assert data["candles"][-1]["close"] == 102.0
    assert data["last_candle_at"]
    assert data["fetched_at"]
    assert _FakeMarketClient.requested_params["interval"] == "5m"


def test_market_monitor_rejects_unknown_instrument(client):
    response = client.get("/api/market-monitor/UNKNOWN")
    assert response.status_code == 404


def test_market_monitor_rejects_unsupported_interval(client):
    response = client.get("/api/market-monitor/NASDAQ100?interval=2m")
    assert response.status_code == 400


def test_market_monitor_returns_502_when_upstream_has_no_candles(client, monkeypatch):
    from app import main

    _FakeMarketClient.payload = {"chart": {"result": None, "error": None}}
    monkeypatch.setattr(main.httpx, "AsyncClient", _FakeMarketClient)
    response = client.get("/api/market-monitor/SP500?interval=15m")

    assert response.status_code == 502
    assert "Data market sementara tidak tersedia" in response.json()["detail"]
