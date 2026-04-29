class SettledMarketResult:
    STATUS_SETTLED = 'settled'
    STATUS_IGNORED_NON_SETTLED = 'ignored_non_settled'
    STATUS_BLOCKED_MISSING_CONTEXT = 'blocked_missing_context'
    STATUS_INCONSISTENT_SOURCE = 'inconsistent_source'

    OUTPUT_SETTLED_TRADE = 'settled_trade'
    OUTPUT_SETTLED_LIQUIDITY_CHANGE = 'settled_liquidity_change'

    def __init__(
        self,
        *,
        normalized_event_id: str,
        source_event_key: str,
        derivation_status: str,
        settled_outputs: list[dict[str, object]] | None = None,
        error_text: str | None = None,
    ):
        self.normalized_event_id = normalized_event_id
        self.source_event_key = source_event_key
        self.derivation_status = derivation_status
        self.settled_outputs = list(settled_outputs or [])
        self.error_text = error_text

    def to_dict(self) -> dict[str, object]:
        return {
            'normalized_event_id': self.normalized_event_id,
            'source_event_key': self.source_event_key,
            'derivation_status': self.derivation_status,
            'settled_outputs': list(self.settled_outputs),
            'error_text': self.error_text,
        }
