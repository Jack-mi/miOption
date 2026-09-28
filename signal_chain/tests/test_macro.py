from datetime import date

from signal_chain.data import fred
from signal_chain.data.macro import read_macro, refresh_macro


def test_read_macro_parses_supabase_snapshot():
    payload = [
        {"series": "FEDERAL_FUNDS_RATE", "as_of": "2026-09-24", "value": 3.88,
         "source": "fred", "fetched_at": "2026-09-28T00:00:00Z"},
        {"series": "RISK_FREE_3M", "as_of": "2026-09-24", "value": 4.24,
         "source": "fred", "fetched_at": "2026-09-28T00:00:00Z"},
    ]
    points, rows = read_macro("k", get=lambda url, headers: payload)
    assert [p.series for p in points] == ["FEDERAL_FUNDS_RATE", "RISK_FREE_3M"]
    assert points[0].as_of == date(2026, 9, 24)
    assert points[1].value == 4.24
    assert rows[0].id == "supabase" and rows[0].state == "used"


def test_read_macro_requires_key():
    points, rows = read_macro(None)
    assert points == []
    assert rows[0].state == "missing"


def test_refresh_macro_upserts_all_series():
    def get(url, headers=None):
        assert "api_key=fred-key" in url
        for _, series_id in fred.SERIES:
            if f"series_id={series_id}" in url:
                return {"observations": [{"date": "2026-09-24", "value": "4.0"}]}
        raise AssertionError(url)

    posted = {}

    def post(url, headers=None, json=None):
        assert url.endswith("/rest/v1/macro_observations")
        assert headers["Prefer"] == "resolution=merge-duplicates"
        posted["rows"] = json
        return None

    points, rows = refresh_macro("fred-key", "sb-key", get=get, post=post)
    assert len(points) == len(fred.SERIES)
    assert rows[0].state == "used"
    assert {row["series"] for row in posted["rows"]} == {s for s, _ in fred.SERIES}
    assert all(row["source"] == "fred" for row in posted["rows"])


def test_refresh_macro_fails_without_keys():
    points, rows = refresh_macro(None, None)
    assert points == []
    assert rows[0].id == "fred" and rows[0].state == "missing"
