from crypto_trading.events.parser import EventParser
from crypto_trading.execution.order_state_machine import OrderStateMachine


def make_event(status, execution_type, transaction_time, trade_id=0, last_qty="0", accumulated="0"):
    return EventParser().parse({"e": "ORDER_TRADE_UPDATE", "E": transaction_time, "T": transaction_time, "o": {"s": "BTCUSDT", "c": "client-1", "S": "BUY", "o": "LIMIT", "f": "GTC", "q": "0.02", "p": "50000", "ap": "50000", "sp": "0", "x": execution_type, "X": status, "i": 123, "l": last_qty, "z": accumulated, "L": "50000", "N": "USDT", "n": "0.01", "T": transaction_time, "t": trade_id, "m": False, "R": False, "ps": "BOTH", "rp": "0"}})


def test_new_partially_filled_filled():
    machine = OrderStateMachine()
    assert machine.apply(make_event("NEW", "NEW", 1))["order"]["order_status"] == "NEW"
    partial = machine.apply(make_event("PARTIALLY_FILLED", "TRADE", 2, trade_id=10, last_qty="0.01", accumulated="0.01"))
    assert partial["fill"]["trade_id"] == 10
    filled = machine.apply(make_event("FILLED", "TRADE", 3, trade_id=11, last_qty="0.01", accumulated="0.02"))
    assert filled["order"]["order_status"] == "FILLED"
    assert filled["order"]["is_terminal"] is True


def test_new_canceled():
    machine = OrderStateMachine()
    machine.apply(make_event("NEW", "NEW", 1))
    result = machine.apply(make_event("CANCELED", "CANCELED", 2))
    assert result["order"]["order_status"] == "CANCELED"
    assert result["order"]["is_terminal"] is True


def test_new_expired():
    machine = OrderStateMachine()
    machine.apply(make_event("NEW", "NEW", 1))
    result = machine.apply(make_event("EXPIRED", "EXPIRED", 2))
    assert result["order"]["order_status"] == "EXPIRED"
    assert result["order"]["is_terminal"] is True


def test_duplicate_trade_does_not_generate_duplicate_fill():
    machine = OrderStateMachine()
    trade = make_event("PARTIALLY_FILLED", "TRADE", 2, trade_id=10, last_qty="0.01", accumulated="0.01")
    assert machine.apply(trade)["fill"] is not None
    assert machine.apply(trade)["fill"] is None


def test_older_event_ignored():
    machine = OrderStateMachine()
    machine.apply(make_event("NEW", "NEW", 10))
    result = machine.apply(make_event("CANCELED", "CANCELED", 9))
    assert result["ignored"] is True
    assert result["reason"] == "older event"
