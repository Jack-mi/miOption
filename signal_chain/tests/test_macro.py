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


def test_macro_reload_observes_new_shared_snapshot():
    observations = [[{"series": "CPI", "as_of": "2026-08-01", "value": 1, "source": "fred",
                      "fetched_at": "2026-09-29T00:00:00Z"}],
                    [{"series": "CPI", "as_of": "2026-09-01", "value": 2, "source": "fred",
                      "fetched_at": "2026-09-30T00:00:00Z"}]]

    def get(url, headers):
        return observations.pop(0) if "macro_latest" in url else []

    first, _ = read_macro("k", get=get)
    second, rows = read_macro("k", get=get)
    assert first[0].value == 1 and second[0].value == 2
    assert "尚无刷新状态 CPI" in rows[0].note


def test_refresh_macro_upserts_all_series():
    def get(url, headers=None):
        assert "api_key=fred-key" in url
        for _, series_id in fred.SERIES:
            if f"series_id={series_id}" in url:
                return {"observations": [{"date": "2026-09-24", "value": "4.0"}]}
        raise AssertionError(url)

    posted = {}

    def post(url, headers=None, json=None):
        if url.endswith("macro_observations"):
            assert headers["Prefer"] == "resolution=merge-duplicates"
        posted[url.split("?")[0].rsplit("/", 1)[-1]] = json
        return None

    points, rows = refresh_macro("fred-key", "sb-key", get=get, post=post)
    assert len(points) == len(fred.SERIES)
    assert rows[0].state == "used"
    assert {row["series"] for row in posted["macro_observations"]} == {s for s, _ in fred.SERIES}
    assert all(row["source"] == "fred" for row in posted["macro_observations"])
    assert {row["series"] for row in posted["record_macro_refresh"]["input_rows"]} == {s for s, _ in fred.SERIES}


def test_refresh_macro_fails_without_keys():
    points, rows = refresh_macro(None, None)
    assert points == []
    assert rows[0].id == "fred" and rows[0].state == "missing"


def test_partial_macro_refresh_reports_failure_and_preserves_other_series():
    def get(url, headers=None):
        if "series_id=" + fred.SERIES[0][1] in url:
            raise RuntimeError("FRED unavailable")
        return {"observations": [{"date": "2026-09-24", "value": "4.0"}]}

    posted = {}

    def post(url, headers, json):
        posted[url.split("/")[-1]] = json

    points, rows = refresh_macro("fred-key", "sb-key", get=get, post=post)
    assert len(points) == len(fred.SERIES) - 1
    assert rows[0].state == "missing"
    assert any(item["last_error"] for item in posted["record_macro_refresh"]["input_rows"])
