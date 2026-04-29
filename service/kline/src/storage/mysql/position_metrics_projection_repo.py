from storage.mysql.pool_state_projection_repo import PoolStateProjectionRepository
from storage.mysql.position_metrics_snapshot_projection_repo import PositionMetricsSnapshotProjectionRepository
from storage.mysql.position_state_projection_repo import PositionStateProjectionRepository
from storage.mysql.settled_liquidity_projection_repo import SettledLiquidityProjectionRepository
from storage.mysql.settled_trade_projection_repo import SettledTradeProjectionRepository


class PositionMetricsProjectionRepository:
    def __init__(
        self,
        db,
        *,
        settled_trade_projection_repo=None,
        settled_liquidity_projection_repo=None,
        position_state_projection_repo=None,
        pool_state_projection_repo=None,
        snapshot_projection_repo=None,
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
        self.position_state_projection_repo = (
            position_state_projection_repo
            or PositionStateProjectionRepository(db)
        )
        self.pool_state_projection_repo = (
            pool_state_projection_repo
            or PoolStateProjectionRepository(db)
        )
        self.snapshot_projection_repo = (
            snapshot_projection_repo
            or PositionMetricsSnapshotProjectionRepository(
                position_state_projection_repo=self.position_state_projection_repo,
                pool_state_projection_repo=self.pool_state_projection_repo,
            )
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

    def get_position_basis_snapshot(
        self,
        *,
        owner: str,
        pool_application_id: str,
        status: str = 'active',
    ) -> dict | None:
        return self.position_state_projection_repo.get_position_basis_snapshot(
            owner=owner,
            pool_application_id=pool_application_id,
            status=status,
        )

    def get_pool_state_snapshot(
        self,
        *,
        pool_application_id: str,
    ) -> dict | None:
        return self.pool_state_projection_repo.get_pool_state_snapshot(
            pool_application_id=pool_application_id,
        )

    def get_snapshot_inputs(
        self,
        *,
        owner: str,
        pool_application_id: str,
        status: str = 'active',
    ) -> dict | None:
        return self.snapshot_projection_repo.get_snapshot_inputs(
            owner=owner,
            pool_application_id=pool_application_id,
            status=status,
        )
