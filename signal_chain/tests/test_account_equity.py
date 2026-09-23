from signal_chain.config import load_settings
from signal_chain.risk.account_equity import read_account_equity


def test_unsupported_market_returns_none():
    assert read_account_equity("CN", load_settings()) is None
