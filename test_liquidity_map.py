from pathlib import Path


def test_liquidity_map_documents_source_and_estimation_limits():
    page_path = Path(__file__).resolve().parent / "app" / "static" / "liquidity-map.html"
    page = page_path.read_text(encoding="utf-8")

    assert "https://www.myfxbook.com/forex-market/liquidity" in page
    assert "bukan data order book" in page
    assert "GC=F" in page
    assert "candidate liquidity" in page.lower()
