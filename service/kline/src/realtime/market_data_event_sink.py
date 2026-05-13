import time

from account_codec import AccountCodec
from market.settled_market_result import SettledMarketResult
from realtime.market_data_event import MarketDataEvent


class MarketDataEventSink:
    def __init__(self, queue, *, now_ms=None, account_codec=None):
        self.queue = queue
        self.now_ms = now_ms or self._default_now_ms
        self.account_codec = account_codec or AccountCodec()

    def publish_derivation_batch(self, derivation_batch: list[dict[str, object]]) -> None:
        for event in self.events_from_derivation_batch(derivation_batch):
            self.queue.put_nowait(event)

    def events_from_derivation_batch(self, derivation_batch: list[dict[str, object]]) -> list[MarketDataEvent]:
        events = []
        for item in derivation_batch:
            for output in item.get('settled_outputs') or []:
                event = self._event_from_output(output)
                if event is not None:
                    events.append(event)
        return events

    def _event_from_output(self, output: dict[str, object]) -> MarketDataEvent | None:
        output_type = output.get('settled_output_type')
        if output_type == SettledMarketResult.OUTPUT_SETTLED_TRADE:
            return MarketDataEvent(
                event_type=MarketDataEvent.TYPE_SETTLED_TRADE,
                pool_application=self._pool_application(output),
                token_reversed=str(output.get('side')) == 'sell_token_0',
                transaction_id=self._int_or_none(output.get('transaction_id')),
                event_time_ms=self._int_or_none(output.get('trade_time_ms')),
                updated_at_ms=self.now_ms(),
            )
        if output_type == SettledMarketResult.OUTPUT_SETTLED_LIQUIDITY_CHANGE:
            return MarketDataEvent(
                event_type=MarketDataEvent.TYPE_SETTLED_LIQUIDITY_CHANGE,
                pool_application=self._pool_application(output),
                owner=self._public_owner(output.get('owner')),
                transaction_id=self._int_or_none(output.get('transaction_id')),
                event_time_ms=self._int_or_none(output.get('event_time_ms')),
                updated_at_ms=self.now_ms(),
            )
        return None

    def _pool_application(self, output: dict[str, object]) -> str | None:
        pool_application = output.get('pool_application_id')
        if pool_application is None:
            return None
        parsed = self.account_codec.parse_account(str(pool_application))
        return self.account_codec.format_account(
            chain_id=parsed['chain_id'],
            owner=parsed['owner'],
        )

    def _public_owner(self, owner: object) -> str | None:
        if owner is None:
            return None
        parsed = self.account_codec.parse_account(str(owner))
        return self.account_codec.format_account(
            chain_id=parsed['chain_id'],
            owner=parsed['owner'],
        )

    def _int_or_none(self, value: object) -> int | None:
        if value is None:
            return None
        return int(value)

    def _default_now_ms(self) -> int:
        return int(time.time() * 1000)
