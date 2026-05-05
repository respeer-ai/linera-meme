from query.read_models.position_metrics_replay_facts import PositionMetricsReplayFacts
from query.read_models.position_metrics_replay_summary import PositionMetricsReplaySummary


class PositionMetricsReplayFactsProjectionRepository:
    def __init__(
        self,
        *,
        settled_liquidity_projection_repo,
        settled_pool_history_projection_repo,
    ):
        self.settled_liquidity_projection_repo = settled_liquidity_projection_repo
        self.settled_pool_history_projection_repo = settled_pool_history_projection_repo

    def get_replay_facts(
        self,
        *,
        owner: str,
        pool_application: str,
        pool_id: int,
        opened_at: int | None,
    ) -> PositionMetricsReplayFacts:
        liquidity_history = self.settled_liquidity_projection_repo.get_position_liquidity_history(
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
        )
        pool_transaction_history = self.settled_pool_history_projection_repo.get_pool_transaction_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        return PositionMetricsReplayFacts({
            'liquidity_history': liquidity_history,
            'pool_transaction_history': pool_transaction_history,
            'pool_swap_count_since_open': self.settled_pool_history_projection_repo.get_pool_swap_count_since(
                pool_application=pool_application,
                pool_id=pool_id,
                created_at=opened_at,
            ),
            'pool_history_gap_summary': self.settled_pool_history_projection_repo.get_pool_transaction_gap_summary(
                pool_application=pool_application,
                pool_id=pool_id,
            ),
            'replay_summary': PositionMetricsReplaySummary.from_histories(
                liquidity_history=liquidity_history,
                pool_transaction_history=pool_transaction_history,
            ),
        })
