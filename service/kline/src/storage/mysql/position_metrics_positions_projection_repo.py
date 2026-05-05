from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError
from storage.mysql.settled_liquidity_projection_repo import SettledLiquidityProjectionRepository


class PositionMetricsPositionsProjectionRepository:
    def __init__(
        self,
        db,
        *,
        settled_liquidity_projection_repo=None,
    ):
        self.db = db
        self.settled_liquidity_projection_repo = (
            settled_liquidity_projection_repo
            or SettledLiquidityProjectionRepository(db)
        )

    def get_positions(
        self,
        *,
        owner: str,
        status: str,
    ) -> list[dict]:
        payload = self.settled_liquidity_projection_repo.get_positions(
            owner=owner,
            status=status,
        )
        if payload is None:
            raise ProjectionQueryUnavailableError('positions')
        return payload
