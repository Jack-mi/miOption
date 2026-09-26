import json
import urllib.request

from mioption_runtime.bot.engine import BotEngine, demo_automation
from mioption_runtime.futu.policy import TradePolicy
from mioption_runtime.futu.quote import MockQuoteBackend
from mioption_runtime.futu.trade import Leg, OrderRequest, get_trade_backend
from mioption_runtime.ingress.webhooks import WebhookServer


def test_mock_chain_and_single_leg_order():
    chain = MockQuoteBackend().option_chain("US.SPY")
    assert len(chain) >= 6
    trade = get_trade_backend(prefer_mock=True)
    call = next(c for c in chain if c.option_type == "CALL" and c.strike == 100)
    result = trade.place(
        OrderRequest(
            underlying="US.SPY",
            structure_id="long_call",
            legs=[Leg(code=call.code, side="BUY", qty=1, price=call.ask)],
            notional=100,
        )
    )
    assert result.ok
    assert result.order_id.startswith("mock-")


def test_multi_leg_iron_shape():
    trade = get_trade_backend(prefer_mock=True)
    result = trade.place(
        OrderRequest(
            underlying="US.SPY",
            structure_id="iron_condor",
            legs=[
                Leg(code="P95", side="BUY", qty=1, price=1.0),
                Leg(code="P100", side="SELL", qty=1, price=2.0),
                Leg(code="C105", side="SELL", qty=1, price=2.0),
                Leg(code="C110", side="BUY", qty=1, price=1.0),
            ],
            notional=200,
        )
    )
    assert result.ok
    assert len(result.fills) == 4


def test_webhook_open_and_exit_monitor():
    policy = TradePolicy()
    engine = BotEngine(automations=[demo_automation("h1")], policy=policy, prefer_mock=True)

    def run_webhook(hook_id: str, payload: dict) -> dict:
        return engine.run(
            "webhook",
            webhook_id=hook_id,
            context={"stock": {"last": float(payload.get("last", 1))}},
        )

    server = WebhookServer("127.0.0.1", 0, run_webhook)
    server.start_background()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.port}/hooks/h1",
            data=json.dumps({"last": 120}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        assert body["ok"]
        assert body["runs"][0]["conditions_ok"]
        assert body["runs"][0]["actions"][0]["ok"]
        pid = body["runs"][0]["actions"][0]["position_id"]
        engine.state.managed["positions"][pid]["pnl_pct"] = 55.0
        events = engine.monitor_tick()
        assert events and events[0]["reason"] == "profit_take_pct"
        assert engine.state.managed["positions"][pid]["status"] == "closed"
    finally:
        server.stop()
