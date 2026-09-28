"""点名顺序由代码拒绝，不靠提示词。"""

from signal_chain.agents import session
from signal_chain.agents.gates import deny_reason
from signal_chain.tests.test_context import D0, _market


def test_non_us_is_denied_before_any_agent():
    assert deny_reason("data_agent", {"ticker": "HK.00700"}, today=D0) == "只覆盖美股"
    assert deny_reason("decision_agent", {"ticker": "CN.600519"}, today=D0) == "只覆盖美股"


def test_decision_and_review_wait_for_the_previous_step():
    session.clear()
    assert deny_reason("decision_agent", {"ticker": "US.AAPL"}, today=D0) == "没有快照"
    session.put_market("US.AAPL", D0, _market())
    assert deny_reason("decision_agent", {"ticker": "US.AAPL"}, today=D0) is None
    assert deny_reason("review_agent", {"ticker": "US.AAPL"}, today=D0) == "没有决策记录"
    assert deny_reason("review_agent", {"ticker": "US.AAPL", "load": True}, today=D0) == "review 不能取数"
