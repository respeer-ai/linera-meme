"""Positions read model.

Reads from SettledLiquidityProjectionRepository (stable projection).
This is a single-path projection query — no dual-path fallback.
Returns only Position bounded context fields.

If the repository returns None, raises ProjectionQueryUnavailableError
to signal that the projection data is not yet available.
"""

from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError


class PositionsReadModel:
    def __init__(self, repository, *, virtual_positions_read_model=None):
        self.repository = repository
        self.virtual_positions_read_model = virtual_positions_read_model

    async def get_positions(
        self,
        *,
        owner: str,
        status: str,
    ) -> dict:
        repository_status = 'all' if (status or '').lower() == 'virtual' else status
        payload = self.repository.get_positions(owner=owner, status=repository_status)
        if payload is None:
            raise ProjectionQueryUnavailableError('positions')
        if self.virtual_positions_read_model is not None:
            payload = await self.virtual_positions_read_model.enrich_positions(
                owner=owner,
                status=status,
                positions=payload,
            )
        return {
            'owner': owner,
            'positions': payload,
        }
