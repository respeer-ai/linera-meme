from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError


class SettledPoolHistoryProjectionRepository:
    def __init__(
        self,
        *,
        settled_trade_projection_repo,
        settled_liquidity_projection_repo,
    ):
        self.settled_trade_projection_repo = settled_trade_projection_repo
        self.settled_liquidity_projection_repo = settled_liquidity_projection_repo

    def get_pool_transaction_history(
        self,
        *,
        pool_application: str,
        pool_id: int,
    ) -> list[dict]:
        trade_history = self.settled_trade_projection_repo.get_pool_trade_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        liquidity_history = self.settled_liquidity_projection_repo.get_pool_liquidity_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        if trade_history is None or liquidity_history is None:
            raise ProjectionQueryUnavailableError('pool_transaction_history')
        history = list(trade_history) + list(liquidity_history)
        history.sort(
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
                row.get('transaction_type') or '',
            ),
        )
        return history

    def get_pool_swap_count_since(
        self,
        *,
        pool_application: str,
        pool_id: int,
        created_at: int | None,
    ) -> int:
        history = self.get_pool_transaction_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        lower_bound = int(created_at or 0)
        return sum(
            1
            for row in history
            if int(row.get('created_at') or 0) >= lower_bound
            and row.get('transaction_type') in {'BuyToken0', 'SellToken0'}
        )

    def get_pool_transaction_gap_summary(
        self,
        *,
        pool_application: str,
        pool_id: int,
    ) -> dict:
        history = self.get_pool_transaction_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        transaction_ids = sorted(
            {
                int(row['transaction_id'])
                for row in history
                if row.get('transaction_id') is not None
            }
        )
        if not transaction_ids:
            return {
                'has_internal_gaps': False,
                'start_id': None,
                'end_id': None,
                'missing_count': 0,
                'missing_ids_sample': [],
                'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
            }
        return {
            'has_internal_gaps': False,
            'start_id': transaction_ids[0],
            'end_id': transaction_ids[-1],
            'missing_count': 0,
            'missing_ids_sample': [],
            'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
        }
