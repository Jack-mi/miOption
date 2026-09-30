from datetime import date, datetime

from signal_chain.sessions import align_futu_quote, hk_quote_session, session_for


def test_hk_session_and_quote_alignment():
    assert session_for("HK", date(2026, 10, 1)) == date(2026, 9, 30)
    assert session_for("HK", date(2026, 9, 30),
                       now=datetime(2026, 9, 30, 17, 34)) == date(2026, 9, 30)
    assert session_for("HK", date(2026, 9, 30),
                       now=datetime(2026, 9, 30, 8, 59)) == date(2026, 9, 29)
    assert hk_quote_session("2026-09-30 16:07:55") == date(2026, 9, 30)
    payload = {"quote": {"update_time": "2026-09-30 16:07:55", "session_date": "wrong"}}
    assert align_futu_quote(payload, market="HK")["quote"]["session_date"] == "2026-09-30"
