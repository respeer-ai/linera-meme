from query.read_models.position_metrics_replay_summary import PositionMetricsReplaySummary


class PositionMetricsReplayFacts:
    def __init__(self, payload: dict | None):
        self.payload = payload or {}

    def liquidity_history(self) -> list[dict]:
        return self.payload['liquidity_history']

    def pool_transaction_history(self) -> list[dict]:
        return self.payload['pool_transaction_history']

    def pool_swap_count_since_open(self) -> int:
        return self.payload['pool_swap_count_since_open']

    def pool_history_gap_summary(self) -> dict:
        return self.payload['pool_history_gap_summary']

    def replay_summary(self) -> PositionMetricsReplaySummary:
        payload = self.payload.get('replay_summary')
        if isinstance(payload, PositionMetricsReplaySummary):
            return payload
        return PositionMetricsReplaySummary(payload)
