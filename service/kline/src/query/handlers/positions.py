"""Lightweight positions list handler.

Bounded context: Position (aggregate view).
This handler provides a list of positions with basic aggregated data.
It MUST NOT compute or return fees, principal, or redeemable amounts.
Those belong to the PositionMetrics bounded context at /position-metrics.
"""


class PositionsHandler:
    def __init__(self, read_model, serializer):
        self.read_model = read_model
        self.serializer = serializer

    async def get_positions(self, **kwargs):
        payload = await self.read_model.get_positions(**kwargs)
        return self.serializer.serialize_positions(payload)
