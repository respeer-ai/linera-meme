from storage.mysql.settled_liquidity_projection_repo import SettledLiquidityProjectionRepository
from storage.mysql.settled_trade_projection_repo import SettledTradeProjectionRepository


class ProjectionRepository:
    """Bridge phase-1 query models onto the existing Db implementation."""

    def __init__(
        self,
        db,
        settled_trade_projection_repo=None,
        settled_liquidity_projection_repo=None,
    ):
        self.db = db
        self.settled_trade_projection_repo = (
            settled_trade_projection_repo
            or SettledTradeProjectionRepository(db)
        )
        self.settled_liquidity_projection_repo = (
            settled_liquidity_projection_repo
            or SettledLiquidityProjectionRepository(db)
        )

    def get_candles(
        self,
        *,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> tuple[int | None, str | None, str, str, list[dict]]:
        settled = self.settled_trade_projection_repo.get_candles(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        if settled is not None:
            return settled
        return self.db.get_kline(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )

    def get_candles_information(
        self,
        *,
        token_0: str,
        token_1: str,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> dict:
        settled = self.settled_trade_projection_repo.get_candles_information(
            token_0=token_0,
            token_1=token_1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        if settled is not None:
            return settled
        return self.db.get_kline_information(
            token_0=token_0,
            token_1=token_1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )

    def get_transactions(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
        start_at: int,
        end_at: int,
    ) -> list[dict]:
        settled = self.settled_trade_projection_repo.get_transactions(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
        )
        if settled is not None:
            return settled
        return self.db.get_transactions(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
        )

    def get_transactions_information(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
    ) -> dict:
        settled = self.settled_trade_projection_repo.get_transactions_information(
            token_0=token_0,
            token_1=token_1,
        )
        if settled is not None:
            return settled
        return self.db.get_transactions_information(
            token_0=token_0,
            token_1=token_1,
        )

    def get_positions(
        self,
        *,
        owner: str,
        status: str,
    ) -> list[dict]:
        settled = self.settled_liquidity_projection_repo.get_positions(
            owner=owner,
            status=status,
        )
        if settled is not None:
            return settled
        return self.db.get_positions(owner=owner, status=status)

    def get_position_liquidity_history(
        self,
        *,
        owner: str,
        pool_application: str,
        pool_id: int,
    ) -> list[dict]:
        settled = self.settled_liquidity_projection_repo.get_position_liquidity_history(
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
        )
        if settled is not None:
            return settled
        return self.db.get_position_liquidity_history(
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
        )

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
        if trade_history is not None and liquidity_history is not None:
            history = list(trade_history) + list(liquidity_history)
            history.sort(
                key=lambda row: (
                    int(row.get('created_at') or 0),
                    int(row.get('transaction_id') or 0),
                    row.get('transaction_type') or '',
                ),
            )
            return history
        return self.db.get_pool_transaction_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )

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
