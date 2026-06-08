from decimal import Decimal

from account_codec import AccountCodec
from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot


class PositionMetricsProjectionPayloadAdapter:
    def __init__(
        self,
        *,
        display_quantum: Decimal = Decimal('0.000000000000000001'),
        account_codec: AccountCodec | None = None,
    ):
        self.display_quantum = display_quantum
        self.account_codec = account_codec or AccountCodec()

    def build_payload(
        self,
        *,
        position: dict,
        snapshot_inputs,
    ) -> dict:
        position_basis_snapshot = self._position_basis_snapshot(snapshot_inputs.position_basis_snapshot())
        pool_state_snapshot = self._pool_state_snapshot(snapshot_inputs.pool_state_snapshot())
        if pool_state_snapshot.raw() is None:
            raise RuntimeError('position_metrics_pool_state_snapshot_unavailable')

        current_liquidity = self._position_liquidity(position=position, position_basis_snapshot=position_basis_snapshot)
        if current_liquidity is None:
            raise RuntimeError('position_metrics_position_liquidity_unavailable')
        current_total_supply = self._decimal_or_none(
            pool_state_snapshot.current_total_supply()
        ) or self._decimal_or_none(
            pool_state_snapshot.fee_free_total_supply()
        )
        current_reserve_0 = self._decimal_or_none(
            pool_state_snapshot.current_reserve_0()
        ) or self._decimal_or_none(
            pool_state_snapshot.fee_free_reserve_0()
        )
        current_reserve_1 = self._decimal_or_none(
            pool_state_snapshot.current_reserve_1()
        ) or self._decimal_or_none(
            pool_state_snapshot.fee_free_reserve_1()
        )
        if (
            current_liquidity is None
            or current_total_supply is None
            or current_total_supply <= Decimal('0')
            or current_reserve_0 is None
            or current_reserve_1 is None
        ):
            raise RuntimeError('position_metrics_projection_payload_incomplete')

        redeemable_amount0 = self._serialize_decimal(current_liquidity * current_reserve_0 / current_total_supply)
        redeemable_amount1 = self._serialize_decimal(current_liquidity * current_reserve_1 / current_total_supply)
        fee_to_account = position_basis_snapshot.semantic_facts().fee_to_account_latest_known()

        return {
            'data': {
                'pool': {
                    'fee_to': self._account_payload(fee_to_account),
                },
                'totalSupply': self._serialize_decimal(current_total_supply),
                'virtualInitialLiquidity': pool_state_snapshot.virtual_initial_liquidity(),
                'liquidity': {
                    'liquidity': self._serialize_decimal(current_liquidity),
                    'amount0': redeemable_amount0,
                    'amount1': redeemable_amount1,
                },
            }
        }

    def _position_liquidity(
        self,
        *,
        position: dict,
        position_basis_snapshot,
    ) -> Decimal | None:
        if (
            position.get('position_kind') in (None, '', 'recorded')
            and not bool(position.get('is_virtual_position'))
        ):
            return self._decimal_or_none(position.get('current_liquidity'))
        return (
            self._decimal_or_none(position_basis_snapshot.current_liquidity())
            or self._decimal_or_none(position.get('current_liquidity'))
        )

    def _position_basis_snapshot(self, snapshot) -> PositionMetricsPositionBasisSnapshot:
        if isinstance(snapshot, PositionMetricsPositionBasisSnapshot):
            return snapshot
        return PositionMetricsPositionBasisSnapshot(snapshot)

    def _pool_state_snapshot(self, snapshot) -> PositionMetricsPoolStateSnapshot:
        if isinstance(snapshot, PositionMetricsPoolStateSnapshot):
            return snapshot
        return PositionMetricsPoolStateSnapshot(snapshot)

    def _decimal_or_none(self, value):
        if value in (None, ''):
            return None
        return Decimal(str(value))

    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        if value == 0:
            return '0'
        return format(value.quantize(self.display_quantum).normalize(), 'f')

    def _account_payload(self, account: str | None) -> dict | None:
        return self.account_codec.payload_from_public_account(account)
