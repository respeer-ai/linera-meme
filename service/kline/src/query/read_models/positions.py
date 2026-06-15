"""Positions read model.

Reads from SettledLiquidityProjectionRepository (stable projection).
This is a single-path projection query — no dual-path fallback.
Returns only Position bounded context fields.

If the repository returns None, raises ProjectionQueryUnavailableError
to signal that the projection data is not yet available.
"""

from decimal import Decimal, InvalidOperation

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
        normalized_status = (status or 'active').lower()
        repository_status = 'all' if normalized_status in {'active', 'all', 'virtual'} else normalized_status
        payload = self.repository.get_positions(owner=owner, status=repository_status)
        if payload is None:
            raise ProjectionQueryUnavailableError('positions')
        if self.virtual_positions_read_model is not None:
            payload = await self.virtual_positions_read_model.enrich_positions(
                owner=owner,
                status='all',
                positions=payload,
            )
        return {
            'owner': owner,
            'positions': self._display_positions(payload, normalized_status),
        }

    def _display_positions(self, positions: list[dict], status: str) -> list[dict]:
        merged = {}
        passthrough = []
        for position in positions:
            key = (
                position.get('pool_application'),
                position.get('pool_id'),
                position.get('token_0'),
                position.get('token_1'),
            )
            if position.get('is_virtual_position'):
                base = merged.get(key) or self._synthetic_display_position(position)
                merged[key] = self._merge_virtual_position(base, position)
                continue
            if key in merged:
                merged[key] = self._merge_recorded_position(merged[key], position)
                continue
            merged[key] = self._normalize_display_position(position)

        for position in merged.values():
            if status == 'active' and position.get('status') != 'active':
                continue
            if status == 'closed' and position.get('status') != 'closed':
                continue
            if status == 'virtual':
                continue
            passthrough.append(position)

        passthrough.sort(
            key=lambda row: (
                -(row.get('closed_at') if status == 'closed' else row.get('updated_at') or 0),
                row.get('pool_id') or 0,
            ),
        )
        return passthrough

    def _normalize_display_position(self, position: dict) -> dict:
        normalized = dict(position)
        normalized.setdefault('position_kind', None)
        normalized.setdefault('is_virtual_position', None)
        return normalized

    def _synthetic_display_position(self, position: dict) -> dict:
        return {
            **position,
            'status': position.get('status') or 'active',
            'position_kind': position.get('position_kind'),
            'is_virtual_position': position.get('is_virtual_position'),
            'closed_at': None,
            'current_liquidity': '0',
            'added_liquidity': '0',
            'removed_liquidity': '0',
            'add_tx_count': 0,
            'remove_tx_count': 0,
        }

    def _merge_recorded_position(self, base: dict, position: dict) -> dict:
        merged = dict(position)
        merged['virtual_initial_amount0'] = base.get('virtual_initial_amount0')
        merged['virtual_initial_amount1'] = base.get('virtual_initial_amount1')
        merged['protocol_fee_receiver_account'] = base.get('protocol_fee_receiver_account')
        merged['protocol_fee_reference_amount0'] = base.get('protocol_fee_reference_amount0')
        merged['protocol_fee_reference_amount1'] = base.get('protocol_fee_reference_amount1')
        merged['current_liquidity'] = position.get('current_liquidity') or '0'
        merged['virtual_current_liquidity'] = base.get('virtual_current_liquidity') or base.get('current_liquidity') or '0'
        if self._positive_amount(merged.get('current_liquidity')):
            merged['status'] = 'active'
            merged['closed_at'] = None
        return merged

    def _merge_virtual_position(self, base: dict, position: dict) -> dict:
        merged = dict(base)
        merged['virtual_initial_amount0'] = position.get('virtual_initial_amount0')
        merged['virtual_initial_amount1'] = position.get('virtual_initial_amount1')
        merged['protocol_fee_receiver_account'] = position.get('protocol_fee_receiver_account')
        merged['protocol_fee_reference_amount0'] = position.get('protocol_fee_reference_amount0')
        merged['protocol_fee_reference_amount1'] = position.get('protocol_fee_reference_amount1')
        merged['current_liquidity'] = base.get('current_liquidity') or '0'
        merged['virtual_current_liquidity'] = position.get('current_liquidity') or '0'
        merged['updated_at'] = max(
            int(base.get('updated_at') or 0),
            int(position.get('updated_at') or 0),
        ) or base.get('updated_at') or position.get('updated_at')
        if self._positive_amount(merged.get('current_liquidity')):
            if merged.get('status') != 'virtual':
                merged['status'] = 'active'
            merged['closed_at'] = None
        return merged

    def _sum_amounts(self, *values: object) -> str:
        total = Decimal('0')
        for value in values:
            try:
                total += Decimal(str(value or '0'))
            except (InvalidOperation, ValueError):
                continue
        return format(total, 'f').rstrip('0').rstrip('.') or '0'

    def _positive_amount(self, value: object) -> bool:
        try:
            return Decimal(str(value or '0')) > Decimal('0')
        except (InvalidOperation, ValueError):
            return False
