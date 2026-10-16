from app.services.econ_calendar import parse_bls_schedule


def test_parse_bls_schedule_normalizes_event_to_utc():
    html = """
    <html><table>
      <tr>
        <td>October 13, 2026</td>
        <td><a href="/news.release/cpi.nr0.htm">Consumer Price Index</a></td>
        <td>8:30 AM</td>
      </tr>
    </table></html>
    """
    events = parse_bls_schedule(html, 2026)
    assert len(events) == 1
    assert events[0]["name"] == "Consumer Price Index"
    assert events[0]["country"] == "US"
    assert events[0]["impact"] == "high"
    assert events[0]["scheduled_at_utc"].endswith("Z")
    assert events[0]["forecast"] is None


def test_parse_bls_schedule_skips_rows_without_timestamp():
    html = """
    <table><tr><td>Consumer Price Index</td><td>Coming soon</td></tr></table>
    """
    assert parse_bls_schedule(html, 2026) == []
