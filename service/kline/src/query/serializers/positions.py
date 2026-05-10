"""Position bounded context serializer.

This serializer enforces the boundary between Position (lightweight list view)
and PositionMetrics (computed enrichment). Only fields in ALLOWED_FIELDS
may appear in the /positions response. Adding a field here requires explicit
review of whether it belongs to the Position or PositionMetrics context.
"""


class PositionsSerializer:
    ALLOWED_FIELDS = frozenset({
        'pool_application',
        'pool_id',
        'token_0',
        'token_1',
        'owner',
        'status',
        'current_liquidity',
        'added_liquidity',
        'removed_liquidity',
        'add_tx_count',
        'remove_tx_count',
        'opened_at',
        'updated_at',
        'closed_at',
        'position_kind',
        'is_virtual_position',
        'virtual_initial_amount0',
        'virtual_initial_amount1',
        'owner_is_fee_to',
        'protocol_fee_reference_amount0',
        'protocol_fee_reference_amount1',
    })

    def serialize_positions(self, payload: dict) -> dict:
        if isinstance(payload, dict):
            positions = payload.get('positions', [])
            return {
                'owner': payload.get('owner', ''),
                'positions': self._filter_fields(positions),
            }
        if isinstance(payload, list):
            return self._filter_fields(payload)
        return payload

    def _filter_fields(self, items: list) -> list:
        return [
            {key: item.get(key) for key in self.ALLOWED_FIELDS}
            for item in items
        ]
