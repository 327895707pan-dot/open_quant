# Architecture

The system is event-driven.

```text
Binance User Data Stream
    -> CryptoDuckDBStore.raw_events
    -> EventParser
    -> EventBus
    -> OrderStore / AccountStore / PositionStore
    -> DemoStrategy
    -> RiskManager
    -> OrderManager
    -> Binance Futures REST
```

The first durable step is raw event persistence. This makes parser or state bugs
replayable without relying on Binance to resend a message.

`EventParser` translates Binance payloads into standard event classes. `EventBus`
decouples transport from state stores and strategies. Stores only consume
standard events and write through `CryptoDuckDBStore`.

The execution layer never assumes an order is filled just because REST accepted
it. It waits for `ORDER_TRADE_UPDATE`.
