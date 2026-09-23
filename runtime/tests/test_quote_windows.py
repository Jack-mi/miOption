from datetime import date

from mioption_runtime.futu.quote import chain_date_windows, jsonable, peek_windows_after


def test_sixty_day_windows_cover_today_plus_sixty():
    windows = chain_date_windows(60, today=date(2026, 9, 7))
    assert windows == [
        ("2026-09-07", "2026-10-06"),
        ("2026-10-07", "2026-11-05"),
        ("2026-11-06", "2026-11-06"),
    ]
    assert windows[-1][1] == "2026-11-06"


def test_peek_windows_follow_horizon():
    assert peek_windows_after("2026-11-06") == [
        ("2026-11-07", "2026-12-06"),
        ("2026-12-07", "2027-01-05"),
    ]


def test_jsonable_drops_nan():
    assert jsonable(float("nan")) is None
    assert jsonable(1.5) == 1.5


def test_jsonable_drops_nan():
    assert jsonable(float("nan")) is None
    assert jsonable(1.5) == 1.5
