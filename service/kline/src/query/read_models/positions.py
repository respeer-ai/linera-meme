"""Positions read model.

Reads from SettledLiquidityProjectionRepository (stable projection).
This is a single-path projection query — no dual-path fallback.
Returns only Position bounded context fields.

If the repository returns None, raises ProjectionQueryUnavailableError
to signal that the projection data is not yet available.
"""

from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError


class PositionsReadModel:
    def __init__(self, repository):
        self.repository = repository

    def get_positions(
        self,
        *,
        owner: str,
        status: str,
    ) -> dict:
        payload = self.repository.get_positions(owner=owner, status=status)
        if payload is None:
            raise ProjectionQueryUnavailableError('positions')
        return {
            'owner': owner,
            'positions': payload,
        }
