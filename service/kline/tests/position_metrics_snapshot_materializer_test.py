import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.position_metrics_snapshot_materializer import PositionMetricsSnapshotMaterializer  # noqa: E402
from market.position_metrics_snapshot_builder import PositionMetricsSnapshotBuilder  # noqa: E402
from market.settled_output_batch_factory import SettledOutputBatchFactory  # noqa: E402
from position_metrics_swap_math_support import PositionMetricsSwapMathSupport  # noqa: E402
from position_metrics_value_support import PositionMetricsValueSupport  # noqa: E402


class PositionMetricsSnapshotMaterializerTest(unittest.TestCase):
    ATTOS_SCALE = 10 ** 18

    class FakeValueSupport:
        def to_attos(self, value):
            if value is None:
                return None
            return int(value)

        def from_attos(self, value):
            return value

        def serialize_decimal(self, value):
            return str(value)

    class FakeSnapshotBuilder:
        def __init__(self, *, should_fail=False):
            self.should_fail = should_fail
            self.calls = []
            self.value_support = PositionMetricsSnapshotMaterializerTest.FakeValueSupport()

        def build_materialization_plan(self, output_batch):
            self.calls.append(output_batch)
            if self.should_fail:
                raise RuntimeError('snapshot rebuild failed')
            return {
                'pool_states': [{'pool_state_id': 'pool-1'}],
                'position_replacements': [
                    {
                        'owner': 'chain-user:owner-a',
                        'pool_application_id': 'chain-a:pool-app',
                        'states': [{'position_state_id': 'pos-1'}],
                    }
                ],
                'affected_pool_count': 1,
                'affected_position_count': 1,
            }

        def apply_pool_state(self, state, output):
            return state

        def _serialize_attos(self, value):
            return str(value or 0)

    class FakePositionStateSnapshotRepository:
        def __init__(self, stored_state=None):
            self.calls = []
            self.stored_state = stored_state

        def replace_position_states(self, **kwargs):
            self.calls.append(dict(kwargs))
            return len(kwargs['states'])

        def get_position_state(self, *, owner, pool_application_id):
            return self.stored_state

    class FakePoolStateSnapshotRepository:
        def __init__(self, stored_state=None):
            self.calls = []
            self.stored_state = stored_state

        def upsert_pool_states(self, states):
            self.calls.append(list(states))
            return len(states)

        def get_pool_state(self, *, pool_application_id):
            return self.stored_state


    def _real_snapshot_builder(self):
        from decimal import Decimal
        value_support = PositionMetricsValueSupport(
            attos_scale=self.ATTOS_SCALE,
            display_quantum=Decimal('0.000000000000000001'),
            epsilon=Decimal('0.000000000001'),
            liquidity_mint_tolerance_attos=100,
            swap_out_tolerance_attos=1,
        )
        swap_math = PositionMetricsSwapMathSupport(
            to_attos=value_support.to_attos,
            from_attos=value_support.from_attos,
            swap_fee_numerator=997,
            swap_fee_denominator=1000,
            swap_out_tolerance_attos=1,
        )
        builder = PositionMetricsSnapshotBuilder(
            snapshot_materialization_inputs_repository=None,
            attos_scale=self.ATTOS_SCALE,
        )
        builder.value_support = value_support
        builder.swap_math_support = swap_math

        def build_materialization_plan(output_batch):
            return {
                'pool_states': [],
                'position_replacements': [],
                'affected_pool_count': 0,
                'affected_position_count': 0,
            }

        builder.build_materialization_plan = build_materialization_plan
        return builder


    def test_incremental_materializer_accepts_settled_output_contract_fields(self):
        pos_repo = self.FakePositionStateSnapshotRepository(stored_state=None)
        pool_repo = self.FakePoolStateSnapshotRepository(stored_state={
            'current_reserve_0': '1000',
            'current_reserve_1': '1000',
            'current_total_supply': '1000',
            'current_k_last': '1000',
            'pending_protocol_fee': '0',
            'total_minted_protocol_fee': '0',
            'swap_count': '0',
            'last_trade_time_ms': '0',
            'last_liquidity_event_time_ms': '0',
            'last_transaction_id': '0',
        })
        materializer = PositionMetricsSnapshotMaterializer(
            snapshot_builder=self._real_snapshot_builder(),
            position_state_snapshot_repository=pos_repo,
            pool_state_snapshot_repository=pool_repo,
        )
        outputs = [
            {
                'settled_output_type': 'settled_liquidity_change',
                'pool_application_id': 'pool-app',
                'pool_chain_id': 'pool-chain',
                'change_type': 'add_liquidity',
                'owner': 'user-a',
                'liquidity_delta': '10000000000000000000',
                'amount_0_delta': '100000000000000000000',
                'amount_1_delta': '100000000000000000000',
                'event_time_ms': 1000,
                'transaction_id': 1,
            },
            {
                'settled_output_type': 'settled_trade',
                'pool_application_id': 'pool-app',
                'pool_chain_id': 'pool-chain',
                'side': 'buy_token_0',
                'amount_0_in': '0',
                'amount_0_out': '9872000000000000000',
                'amount_1_in': '10000000000000000000',
                'amount_1_out': '0',
                'trade_time_ms': 2000,
                'transaction_id': 2,
            },
        ]
        batch = SettledOutputBatchFactory().build(outputs)
        result = materializer.materialize_output_batch(batch)

        self.assertFalse(result['degraded'])
        self.assertEqual(len(pos_repo.calls), 1)
        position_state = pos_repo.calls[0]['states'][0]
        self.assertEqual(position_state['status'], 'active')
        self.assertEqual(position_state['basis_type'], 'add_liquidity')
        self.assertEqual(position_state['basis_time_ms'], 1000)
        self.assertNotEqual(position_state['current_liquidity'], '0')
        pool_state = pool_repo.calls[0][0]
        self.assertEqual(pool_state['last_transaction_id'], 2)
        self.assertEqual(pool_state['last_trade_time_ms'], 2000)
        self.assertNotEqual(pool_state['current_total_supply'], '0')
        self.assertNotEqual(pool_state['current_reserve_0'], '1000')


    def test_virtual_initial_liquidity_updates_pool_but_not_position(self):
        pos_repo = self.FakePositionStateSnapshotRepository(stored_state=None)
        pool_repo = self.FakePoolStateSnapshotRepository(stored_state=None)
        materializer = PositionMetricsSnapshotMaterializer(
            snapshot_builder=self._real_snapshot_builder(),
            position_state_snapshot_repository=pos_repo,
            pool_state_snapshot_repository=pool_repo,
        )
        outputs = [{
            'settled_output_type': 'settled_liquidity_change',
            'pool_application_id': 'pool-app',
            'pool_chain_id': 'pool-chain',
            'change_type': 'add_liquidity',
            'owner': 'user-a',
            'liquidity_delta': '10000000000000000000',
            'amount_0_delta': '100000000000000000000',
            'amount_1_delta': '100000000000000000000',
            'is_position_liquidity': False,
            'liquidity_semantics': 'virtual_initial_liquidity',
            'event_time_ms': 1000,
            'transaction_id': 1,
        }]
        batch = SettledOutputBatchFactory().build(outputs)
        result = materializer.materialize_output_batch(batch)

        self.assertFalse(result['degraded'])
        self.assertEqual(pos_repo.calls, [])
        self.assertEqual(len(pool_repo.calls), 1)
        pool_state = pool_repo.calls[0][0]
        self.assertEqual(pool_state['current_reserve_0'], '100')
        self.assertEqual(pool_state['current_reserve_1'], '100')
        self.assertEqual(pool_state['current_total_supply'], '100')

    def test_incremental_pool_state_swap_updates_reserves_and_pending(self):
        stored = {
            'current_reserve_0': '1000',
            'current_reserve_1': '1000',
            'current_total_supply': '1000',
            'current_k_last': '1000',
            'pending_protocol_fee': '0',
            'total_minted_protocol_fee': '0',
            'swap_count': '0',
            'last_trade_time_ms': '0',
            'last_liquidity_event_time_ms': '0',
            'last_transaction_id': '0',
        }
        pool_repo = self.FakePoolStateSnapshotRepository(stored_state=stored)
        materializer = PositionMetricsSnapshotMaterializer(
            snapshot_builder=self._real_snapshot_builder(),
            position_state_snapshot_repository=self.FakePositionStateSnapshotRepository(),
            pool_state_snapshot_repository=pool_repo,
        )
        outputs = [{
            'settled_output_type': 'settled_trade',
            'pool_application_id': 'pool-app',
            'transaction_type': 'BuyToken0',
            'amount_0_in': '0',
            'amount_0_out': '9.872',
            'amount_1_in': '10',
            'amount_1_out': '0',
            'trade_time_ms': 1000,
            'transaction_id': 1,
        }]
        batch = SettledOutputBatchFactory().build(outputs)
        result = materializer.materialize_output_batch(batch)

        self.assertFalse(result['degraded'])
        self.assertEqual(len(pool_repo.calls), 1)
        upserted = pool_repo.calls[0][0]
        self.assertNotEqual(upserted['current_reserve_0'], '1000')
        self.assertNotEqual(upserted['pending_protocol_fee'], '0')

    def test_incremental_position_state_add_creates_active(self):
        pos_repo = self.FakePositionStateSnapshotRepository(stored_state=None)
        pool_repo = self.FakePoolStateSnapshotRepository()
        materializer = PositionMetricsSnapshotMaterializer(
            snapshot_builder=self._real_snapshot_builder(),
            position_state_snapshot_repository=pos_repo,
            pool_state_snapshot_repository=pool_repo,
        )
        outputs = [{
            'settled_output_type': 'settled_liquidity_change',
            'pool_application_id': 'pool-app',
            'transaction_type': 'AddLiquidity',
            'owner': 'user-a',
            'liquidity': '10',
            'amount_0_in': '100', 'amount_0_out': '0',
            'amount_1_in': '100', 'amount_1_out': '0',
            'created_at': 1000, 'transaction_id': 1,
        }]
        batch = SettledOutputBatchFactory().build(outputs)
        result = materializer.materialize_output_batch(batch)

        self.assertFalse(result['degraded'])
        self.assertEqual(len(pos_repo.calls), 1)
        call = pos_repo.calls[0]
        self.assertEqual(call['owner'], 'user-a')
        self.assertEqual(call['pool_application_id'], 'pool-app')
        state = call['states'][0]
        self.assertEqual(state['status'], 'active')
        self.assertNotEqual(state['current_liquidity'], '0')
        self.assertEqual(state['basis_type'], 'add_liquidity')

    def test_incremental_position_state_remove_closes(self):
        stored = {
            'current_liquidity': '10',
            'status': 'active',
            'state_payload_json': {
                'added_liquidity': '10', 'removed_liquidity': '0',
                'current_round_liquidity_event_count': 1,
                'current_round_started_at': 1000,
                'current_round_started_transaction_id': 1,
            },
        }
        pos_repo = self.FakePositionStateSnapshotRepository(stored_state=stored)
        pool_repo = self.FakePoolStateSnapshotRepository()
        materializer = PositionMetricsSnapshotMaterializer(
            snapshot_builder=self._real_snapshot_builder(),
            position_state_snapshot_repository=pos_repo,
            pool_state_snapshot_repository=pool_repo,
        )
        outputs = [{
            'settled_output_type': 'settled_liquidity_change',
            'pool_application_id': 'pool-app',
            'transaction_type': 'RemoveLiquidity',
            'owner': 'user-a',
            'liquidity': '10',
            'amount_0_in': '0', 'amount_0_out': '100',
            'amount_1_in': '0', 'amount_1_out': '100',
            'created_at': 2000, 'transaction_id': 2,
        }]
        batch = SettledOutputBatchFactory().build(outputs)
        result = materializer.materialize_output_batch(batch)

        self.assertFalse(result['degraded'])
        call = pos_repo.calls[0]
        self.assertEqual(call['states'][0]['status'], 'closed')
        self.assertEqual(call['states'][0]['current_liquidity'], '0')


    def test_repair_position_state_gaps_materializes_only_repository_gap_batches(self):
        class FakeGapRepository:
            def __init__(self):
                self.calls = 0

            def list_position_snapshot_gap_changes(self, *, limit):
                self.calls += 1
                if self.calls == 1:
                    return [{
                        'settled_output_type': 'settled_liquidity_change',
                        'pool_application_id': 'pool-app',
                        'transaction_type': 'RemoveLiquidity',
                        'owner': 'user-a',
                        'liquidity': '10',
                        'amount_0_in': '0', 'amount_0_out': '100',
                        'amount_1_in': '0', 'amount_1_out': '100',
                        'created_at': 2000, 'transaction_id': 2,
                    }]
                return []

        stored = {
            'current_liquidity': '10',
            'status': 'active',
            'state_payload_json': '{\"added_liquidity\":\"10\",\"removed_liquidity\":\"0\",\"last_transaction_id\":1}',
        }
        pos_repo = self.FakePositionStateSnapshotRepository(stored_state=stored)
        materializer = PositionMetricsSnapshotMaterializer(
            snapshot_builder=self._real_snapshot_builder(),
            position_state_snapshot_repository=pos_repo,
            pool_state_snapshot_repository=self.FakePoolStateSnapshotRepository(),
        )

        result = materializer.repair_position_state_gaps(
            settled_liquidity_change_repository=FakeGapRepository(),
            settled_output_batch_factory=SettledOutputBatchFactory(),
            batch_limit=10,
            max_batches=2,
        )

        self.assertFalse(result['degraded'])
        self.assertEqual(result['batches'], 1)
        self.assertEqual(result['repaired_output_count'], 1)
        self.assertEqual(pos_repo.calls[0]['states'][0]['status'], 'closed')
        self.assertEqual(pos_repo.calls[0]['states'][0]['current_liquidity'], '0')



if __name__ == '__main__':
    unittest.main()
