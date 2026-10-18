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
