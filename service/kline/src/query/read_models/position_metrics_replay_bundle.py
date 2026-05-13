from query.read_models.position_metrics_replay_facts import PositionMetricsReplayFacts
from query.read_models.position_metrics_replay_summary import PositionMetricsReplaySummary


class PositionMetricsReplayBundle:
    def __init__(self, payload: dict | PositionMetricsReplayFacts | None):
        if isinstance(payload, PositionMetricsReplayFacts):
            self.facts = payload
        else:
            self.facts = PositionMetricsReplayFacts(payload)

    def liquidity_history(self) -> list[dict]:
        return self.facts.liquidity_history()

    def pool_transaction_history(self) -> list[dict]:
        return self.facts.pool_transaction_history()

    def pool_swap_count_since_open(self) -> int:
        return self.facts.pool_swap_count_since_open()

    def pool_history_gap_summary(self) -> dict:
        return self.facts.pool_history_gap_summary()

    def replay_summary(self) -> PositionMetricsReplaySummary:
        return self.facts.replay_summary()
