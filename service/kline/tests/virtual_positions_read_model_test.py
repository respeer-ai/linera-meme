import asyncio
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.virtual_positions import VirtualPositionsReadModel  # noqa: E402


class VirtualPositionsReadModelTest(unittest.TestCase):
    def test_enrich_positions_adds_virtual_initial_liquidity_position_from_projection_snapshot(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                self.owner = owner
                return [{
                    'pool_application': 'chain-a:0xpool-app',
                    'pool_id': 7,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': owner,
                    'opened_at': 1000,
                    'updated_at': 1000,
                    'add_tx_count': 1,
                }]

        class FakeSnapshotInputsProjectionRepository:
            class FakePoolStateProjectionRepository:
                def list_pool_state_snapshots(self):
                    return []

            def __init__(self):
                self.pool_state_projection_repo = self.FakePoolStateProjectionRepository()

            def get_snapshot_inputs(self, *, owner, pool_application_id, status):
                return {
                    'position_basis_snapshot': {
                        'current_liquidity': '5',
                        'semantic_facts': {},
                    },
                    'pool_state_snapshot': {
                        'state_payload_json': {
                            'virtual_initial_liquidity': True,
                            'fee_to_account_latest_known': None,
                        },
                    },
                }

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=FakeSnapshotInputsProjectionRepository(),
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-a:owner-a',
            status='active',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertTrue(result[0]['is_virtual_position'])
        self.assertEqual(result[0]['current_liquidity'], '5')
        self.assertEqual(result[0]['added_liquidity'], '5')
        self.assertEqual(result[0]['removed_liquidity'], '0')

    def test_enrich_positions_falls_back_to_pool_state_snapshots_when_projection_has_no_candidates(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                self.owner = owner
                return []

        class FakeSnapshotInputsProjectionRepository:
            class FakePoolStateProjectionRepository:
                def list_pool_state_snapshots(self):
                    return [{
                        'pool_application_id': 'chain-b:0xpool-app',
                        'last_trade_time_ms': 2000,
                        'last_liquidity_event_time_ms': 1000,
                        'state_payload_json': {
                            'pool_created_metadata': {
                                'token_0': 'DOGE',
                                'token_1': 'TLINERA',
                            },
                        },
                    }]

            def __init__(self):
                self.pool_state_projection_repo = self.FakePoolStateProjectionRepository()

            def get_snapshot_inputs(self, *, owner, pool_application_id, status):
                return {
                    'position_basis_snapshot': {
                        'current_liquidity': '7',
                        'semantic_facts': {},
                    },
                    'pool_state_snapshot': {
                        'state_payload_json': {
                            'virtual_initial_liquidity': True,
                            'fee_to_account_latest_known': None,
                        },
                    },
                }

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=FakeSnapshotInputsProjectionRepository(),
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-b:owner-b',
            status='active',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['pool_application'], 'chain-b:0xpool-app')
        self.assertEqual(result[0]['token_1'], 'TLINERA')
        self.assertEqual(result[0]['pool_id'], 0)
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertTrue(result[0]['is_virtual_position'])
        self.assertEqual(result[0]['current_liquidity'], '7')

    def test_enrich_positions_adds_protocol_fee_receiver_virtual_position_when_owner_has_no_lp(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                return [{
                    'pool_application': 'chain-fee:0xpool-app',
                    'pool_id': 12,
                    'token_0': 'MEME',
                    'token_1': 'TLINERA',
                    'owner': owner,
                    'opened_at': None,
                    'updated_at': 2000,
                    'add_tx_count': 0,
                }]

        class FakeSnapshotInputsProjectionRepository:
            class FakePoolStateProjectionRepository:
                def list_pool_state_snapshots(self):
                    return []

            def __init__(self):
                self.pool_state_projection_repo = self.FakePoolStateProjectionRepository()

            def get_snapshot_inputs(self, *, owner, pool_application_id, status):
                return {
                    'position_basis_snapshot': {
                        'current_liquidity': '0',
                        'semantic_facts': {},
                    },
                    'pool_state_snapshot': {
                        'state_payload_json': {
                            'virtual_initial_liquidity': True,
                            'fee_to_account_latest_known': 'chain-fee:0xfee-owner',
                        },
                    },
                }

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=FakeSnapshotInputsProjectionRepository(),
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-fee:0xfee-owner',
            status='active',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]['position_kind'],
            VirtualPositionsReadModel.SYNTHETIC_PROTOCOL_FEE_RECEIVER_POSITION_KIND,
        )
        self.assertTrue(result[0]['is_virtual_position'])
        self.assertEqual(result[0]['current_liquidity'], '0')
        self.assertEqual(result[0]['added_liquidity'], '0')
        self.assertEqual(result[0]['removed_liquidity'], '0')
        self.assertEqual(result[0]['protocol_fee_reference_amount0'], '0')
        self.assertEqual(result[0]['protocol_fee_reference_amount1'], '0')

    def test_enrich_positions_adds_virtual_initial_liquidity_when_current_liquidity_is_zero(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                return [{
                    'pool_application': 'chain-initial:0xpool-app',
                    'pool_id': 13,
                    'token_0': 'MEME',
                    'token_1': 'TLINERA',
                    'owner': owner,
                    'opened_at': None,
                    'updated_at': 3000,
                    'add_tx_count': 0,
                }]

        class FakeSnapshotInputsProjectionRepository:
            class FakePoolStateProjectionRepository:
                def list_pool_state_snapshots(self):
                    return []

            def __init__(self):
                self.pool_state_projection_repo = self.FakePoolStateProjectionRepository()

            def get_snapshot_inputs(self, *, owner, pool_application_id, status):
                return {
                    'position_basis_snapshot': {
                        'current_liquidity': '0',
                        'basis_amount_0': '10499900',
                        'basis_amount_1': '8720',
                        'semantic_facts': {},
                    },
                    'pool_state_snapshot': {
                        'state_payload_json': {
                            'virtual_initial_liquidity': True,
                            'fee_to_account_latest_known': 'chain-initial:owner-a',
                        },
                    },
                }

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=FakeSnapshotInputsProjectionRepository(),
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-initial:owner-a',
            status='active',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertTrue(result[0]['is_virtual_position'])
        self.assertEqual(result[0]['current_liquidity'], '0')
        self.assertEqual(result[0]['virtual_initial_amount0'], '10499900')
        self.assertEqual(result[0]['virtual_initial_amount1'], '8720')
        self.assertTrue(result[0]['owner_is_fee_to'])
        self.assertEqual(result[0]['protocol_fee_reference_amount0'], '10499900')
        self.assertEqual(result[0]['protocol_fee_reference_amount1'], '8720')

    def test_enrich_positions_uses_closed_basis_snapshot_for_active_virtual_initial_liquidity(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                return [{
                    'pool_application': 'chain-closed:0xpool-app',
                    'pool_id': 14,
                    'token_0': 'MEME',
                    'token_1': 'TLINERA',
                    'owner': owner,
                    'opened_at': None,
                    'updated_at': 4000,
                    'add_tx_count': 0,
                }]

        class FakeSnapshotInputsProjectionRepository:
            class FakePoolStateProjectionRepository:
                def list_pool_state_snapshots(self):
                    return []

            def __init__(self):
                self.pool_state_projection_repo = self.FakePoolStateProjectionRepository()
                self.statuses = []

            def get_snapshot_inputs(self, *, owner, pool_application_id, status):
                self.statuses.append(status)
                if status == 'active':
                    return None
                return {
                    'position_basis_snapshot': {
                        'current_liquidity': '0',
                        'basis_amount_0': '100',
                        'basis_amount_1': '1',
                        'semantic_facts': {},
                    },
                    'pool_state_snapshot': {
                        'state_payload_json': {
                            'virtual_initial_liquidity': True,
                            'fee_to_account_latest_known': None,
                        },
                    },
                }

        snapshot_repo = FakeSnapshotInputsProjectionRepository()
        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=snapshot_repo,
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-closed:owner-a',
            status='active',
            positions=[],
        ))

        self.assertEqual(snapshot_repo.statuses, ['active', 'closed'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'active')
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertEqual(result[0]['virtual_initial_amount0'], '100')
        self.assertEqual(result[0]['virtual_initial_amount1'], '1')

    def test_enrich_positions_works_when_pool_state_snapshots_are_empty(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                return []

        class FakeSnapshotInputsProjectionRepository:
            class FakePoolStateProjectionRepository:
                def list_pool_state_snapshots(self):
                    return []

            def __init__(self):
                self.pool_state_projection_repo = self.FakePoolStateProjectionRepository()

            def get_snapshot_inputs(self, *, owner, pool_application_id, status):
                raise AssertionError('should not be called')

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=FakeSnapshotInputsProjectionRepository(),
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-x:owner-x',
            status='active',
            positions=[],
        ))

        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
