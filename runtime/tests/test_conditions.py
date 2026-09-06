from mioption_runtime.bot.conditions import eval_all, eval_condition
from mioption_runtime.bot.models import Condition


def test_stock_last_gt():
    cond = Condition(family="stock", name="stock.last", op="gt", value=99)
    assert eval_condition(cond, {"stock": {"last": 100}})
    assert not eval_condition(cond, {"stock": {"last": 50}})


def test_eval_all_and():
    conds = [
        Condition(family="stock", name="stock.last", op="gt", value=0),
        Condition(family="position", name="position.open_count", op="lt", value=3),
    ]
    ok, details = eval_all(conds, {"stock": {"last": 1}, "position": {"open_count": 1}})
    assert ok
    assert len(details) == 2
