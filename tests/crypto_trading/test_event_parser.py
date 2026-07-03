from crypto_trading.events.models import AccountUpdateEvent, ListenKeyExpiredEvent, OrderTradeUpdateEvent, UnknownEvent
from crypto_trading.events.parser import EventParser


def order_event(execution_type="NEW", status="NEW", trade_id=0):
    return {
        "e": "ORDER_TRADE_UPDATE",
        "E": 1700000000000,
        "T": 1700000000001,
        "o": {"s": "BTCUSDT", "c": "client-1", "S": "BUY", "o": "LIMIT", "f": "GTC", "q": "0.01", "p": "50000", "ap": "0", "sp": "0", "x": execution_type, "X": status, "i": 123, "l": "0.01" if execution_type == "TRADE" else "0", "z": "0.01" if status == "FILLED" else "0", "L": "50100", "N": "USDT", "n": "0.01", "T": 1700000000002, "t": trade_id, "m": False, "R": False, "wt": "CONTRACT_PRICE", "ot": "LIMIT", "ps": "BOTH", "cp": False, "rp": "1.5", "er": "0"},
    }


def test_parse_order_trade_update_new():
    event = EventParser().parse(order_event())
    assert isinstance(event, OrderTradeUpdateEvent)
    assert event.symbol == "BTCUSDT"
    assert event.order_id == 123
    assert event.original_qty == 0.01
    assert event.execution_type == "NEW"


def test_parse_order_trade_update_trade_filled():
    event = EventParser().parse(order_event("TRADE", "FILLED", 456))
    assert isinstance(event, OrderTradeUpdateEvent)
    assert event.execution_type == "TRADE"
    assert event.order_status == "FILLED"
    assert event.trade_id == 456
    assert event.last_filled_qty == 0.01


def test_parse_account_update():
    raw = {"e": "ACCOUNT_UPDATE", "E": 1, "T": 2, "a": {"m": "ORDER", "B": [{"a": "USDT", "wb": "100", "cw": "80", "bc": "5"}], "P": [{"s": "BTCUSDT", "pa": "0.01", "ep": "50000", "ps": "BOTH"}]}}
    event = EventParser().parse(raw)
    assert isinstance(event, AccountUpdateEvent)
    assert event.reason == "ORDER"
    assert event.balances[0]["a"] == "USDT"
    assert event.positions[0]["s"] == "BTCUSDT"


def test_parse_listen_key_expired():
    event = EventParser().parse({"e": "listenKeyExpired", "E": 1, "listenKey": "abc"})
    assert isinstance(event, ListenKeyExpiredEvent)
    assert event.event_time == 1
    assert event.listen_key == "abc"


def test_parse_unknown_event():
    event = EventParser().parse({"e": "SOMETHING_ELSE", "E": 1})
    assert isinstance(event, UnknownEvent)
    assert event.event_type == "SOMETHING_ELSE"
