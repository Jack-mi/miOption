from signal_chain.config import load_settings
from signal_chain.risk.account_equity import equity_from_accinfo, read_account_equity


def test_unsupported_market_returns_none():
    assert read_account_equity("CN", load_settings()) is None


def test_us_total_assets_convert_with_implied_hkd_rate():
    row = equity_from_accinfo("US", {
        "currency": "HKD",
        "total_assets": 267_177.28,
        "hkd_assets": 254_683.56,
        "usd_assets": 1_568.61,
        "other_assets": 0,
    })
    assert row is not None
    assert row["field"] == "total_assets"
    assert row["currency"] == "USD"
    assert row["original_currency"] == "HKD"
    assert row["fx_source"] == "futu_accinfo_implied"
    assert 7.0 <= row["fx_rate"] <= 8.3
    assert row["value"] == row["original_value"] / row["fx_rate"]
    assert row["note"] is None


def test_us_falls_back_to_usd_cash_without_a_rate():
    row = equity_from_accinfo("US", {
        "currency": "HKD",
        "total_assets": 267_177.28,
        "hkd_assets": 200_000.0,
        "usd_assets": 1_568.61,
        "other_assets": 50_000.0,
    })
    assert row is not None
    assert row["field"] == "usd_assets"
    assert row["value"] == 1_568.61
    assert row["note"] == "仅美元现金，未计入其他币种"
    assert row["fx_rate"] is None
