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
                    'virtual_initial_amount0': '1',
                    'virtual_initial_amount1': '2',
                    'virtual_initial_liquidity': '5',
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
            status='all',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'virtual')
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertTrue(result[0]['is_virtual_position'])
        self.assertEqual(result[0]['current_liquidity'], '5')
        self.assertEqual(result[0]['added_liquidity'], '5')
        self.assertEqual(result[0]['removed_liquidity'], '0')

    def test_enrich_positions_keeps_candidate_protocol_fee_receiver_without_snapshot(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                return [{
                    'pool_application': 'chain-candidate:0xpool-app',
                    'pool_id': 18,
                    'token_0': 'MEME',
                    'token_1': 'TLINERA',
                    'owner': owner,
                    'opened_at': 7000,
                    'updated_at': 7000,
                    'add_tx_count': 1,
                    'virtual_initial_amount0': '10499900',
                    'virtual_initial_amount1': '8720',
                    'virtual_initial_liquidity': '302587.389030012286796095',
                    'protocol_fee_receiver_account': owner,
                }]

        class FakeSnapshotInputsProjectionRepository:
            def get_snapshot_inputs(self, *, owner, pool_application_id, status):
                return None

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=FakeSnapshotInputsProjectionRepository(),
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-candidate:owner-a',
            status='all',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'virtual')
        self.assertEqual(result[0]['protocol_fee_receiver_account'], 'chain-candidate:owner-a')
        self.assertEqual(result[0]['current_liquidity'], '302587.389030012286796095')
        self.assertEqual(result[0]['protocol_fee_reference_amount0'], '10499900')
        self.assertEqual(result[0]['protocol_fee_reference_amount1'], '8720')

    def test_enrich_positions_does_not_create_virtual_position_from_pool_state_without_candidate(self):
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
            status='all',
            positions=[],
        ))

        self.assertEqual(result, [])

    def test_enrich_positions_uses_candidate_and_pool_fee_free_basis_for_virtual_initial_liquidity(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                return [{
                    'pool_application': '0xpool@app-chain',
                    'pool_id': 17,
                    'token_0': 'MEME',
                    'token_1': 'TLINERA',
                    'owner': owner,
                    'opened_at': 2000,
                    'updated_at': 2000,
                    'add_tx_count': 1,
                    'virtual_initial_amount0': '10499900',
                    'virtual_initial_amount1': '8720',
                    'virtual_initial_liquidity': '0',
                }]

        class FakePoolCatalogRepository:
            def list_current_pools(self):
                return [{
                    'pool_application': '0xpool@app-chain',
                    'pool_id': 17,
                    'token_0': 'MEME',
                    'token_1': 'TLINERA',
                }]

        class FakeSnapshotInputsProjectionRepository:
            class FakePoolStateProjectionRepository:
                def list_pool_state_snapshots(self):
                    return [{
                        'pool_application_id': '0xpool@app-chain',
                        'last_trade_time_ms': 3000,
                        'last_liquidity_event_time_ms': 2000,
                        'state_payload_json': {
                            'virtual_initial_liquidity': True,
                            'pool_created_metadata': None,
                            'fee_free_basis': {
                                'from_account': '0xowner@owner-chain',
                                'reserve0_after': '10499900000000000000000000',
                                'reserve1_after': '8720000000000000000000',
                            },
                        },
                    }]

            def __init__(self):
                self.pool_state_projection_repo = self.FakePoolStateProjectionRepository()

            def get_snapshot_inputs(self, *, owner, pool_application_id, status):
                return {
                    'position_basis_snapshot': None,
                    'pool_state_snapshot': {
                        'state_payload_json': {
                            'virtual_initial_liquidity': True,
                            'pool_created_metadata': None,
                            'fee_free_basis': {
                                'from_account': '0xowner@owner-chain',
                                'reserve0_after': '10499900000000000000000000',
                                'reserve1_after': '8720000000000000000000',
                            },
                        },
                    },
                }

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=FakeSnapshotInputsProjectionRepository(),
            pool_catalog_repository=FakePoolCatalogRepository(),
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='0xowner@owner-chain',
            status='virtual',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['pool_application'], '0xpool@app-chain')
        self.assertEqual(result[0]['pool_id'], 17)
        self.assertEqual(result[0]['token_0'], 'MEME')
        self.assertEqual(result[0]['token_1'], 'TLINERA')
        self.assertEqual(result[0]['status'], 'virtual')
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertEqual(result[0]['current_liquidity'], '0')
        self.assertEqual(result[0]['virtual_initial_amount0'], '10499900')
        self.assertEqual(result[0]['virtual_initial_amount1'], '8720')

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
                    'virtual_initial_amount0': '10499900',
                    'virtual_initial_amount1': '8720',
                    'virtual_initial_liquidity': '0',
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
            status='all',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'virtual')
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertEqual(result[0]['protocol_fee_receiver_account'], 'chain-fee:0xfee-owner')
        self.assertTrue(result[0]['is_virtual_position'])
        self.assertEqual(result[0]['current_liquidity'], '0')
        self.assertEqual(result[0]['added_liquidity'], '0')
        self.assertEqual(result[0]['removed_liquidity'], '0')
        self.assertEqual(result[0]['protocol_fee_reference_amount0'], '10499900')
        self.assertEqual(result[0]['protocol_fee_reference_amount1'], '8720')

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
                    'virtual_initial_amount0': '10499900',
                    'virtual_initial_amount1': '8720',
                    'virtual_initial_liquidity': '0',
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
            status='all',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'virtual')
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertTrue(result[0]['is_virtual_position'])
        self.assertEqual(result[0]['current_liquidity'], '0')
        self.assertEqual(result[0]['virtual_initial_amount0'], '10499900')
        self.assertEqual(result[0]['virtual_initial_amount1'], '8720')
        self.assertEqual(result[0]['protocol_fee_receiver_account'], 'chain-initial:owner-a')
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
                    'virtual_initial_amount0': '10499900',
                    'virtual_initial_amount1': '8720',
                    'virtual_initial_liquidity': '0',
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
            status='all',
            positions=[],
        ))

        self.assertEqual(snapshot_repo.statuses, ['active', 'closed'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'virtual')
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertEqual(result[0]['virtual_initial_amount0'], '100')
        self.assertEqual(result[0]['virtual_initial_amount1'], '1')

    def test_enrich_positions_uses_closed_basis_when_active_snapshot_only_has_pool_state(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                return [{
                    'pool_application': 'chain-active-pool-only:0xpool-app',
                    'pool_id': 15,
                    'token_0': 'MEME',
                    'token_1': 'TLINERA',
                    'owner': owner,
                    'opened_at': None,
                    'updated_at': 5000,
                    'add_tx_count': 0,
                    'virtual_initial_amount0': '10499900',
                    'virtual_initial_amount1': '8720',
                    'virtual_initial_liquidity': '0',
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
                pool_state_snapshot = {
                    'state_payload_json': {
                        'virtual_initial_liquidity': True,
                        'fee_to_account_latest_known': None,
                    },
                }
                if status == 'active':
                    return {
                        'position_basis_snapshot': None,
                        'pool_state_snapshot': pool_state_snapshot,
                    }
                return {
                    'position_basis_snapshot': {
                        'current_liquidity': '0',
                        'basis_amount_0': '10499900',
                        'basis_amount_1': '8720',
                        'semantic_facts': {
                            'fee_to_continuity_owner': 'chain-active-pool-only:owner-a',
                        },
                    },
                    'pool_state_snapshot': pool_state_snapshot,
                }

        snapshot_repo = FakeSnapshotInputsProjectionRepository()
        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=snapshot_repo,
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-active-pool-only:owner-a',
            status='all',
            positions=[],
        ))

        self.assertEqual(snapshot_repo.statuses, ['active', 'closed'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'virtual')
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertEqual(result[0]['protocol_fee_receiver_account'], 'chain-active-pool-only:owner-a')
        self.assertEqual(result[0]['protocol_fee_reference_amount0'], '10499900')
        self.assertEqual(result[0]['protocol_fee_reference_amount1'], '8720')

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

    def test_enrich_positions_does_not_include_virtual_positions_in_active_or_closed_filters(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                return [{
                    'pool_application': 'chain-filter:0xpool-app',
                    'pool_id': 16,
                    'token_0': 'MEME',
                    'token_1': 'TLINERA',
                    'owner': owner,
                    'opened_at': None,
                    'updated_at': 6000,
                    'add_tx_count': 0,
                    'virtual_initial_amount0': '10499900',
                    'virtual_initial_amount1': '8720',
                    'virtual_initial_liquidity': '0',
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
                        'basis_amount_0': '100',
                        'basis_amount_1': '1',
                        'semantic_facts': {},
                    },
                    'pool_state_snapshot': {
                        'state_payload_json': {
                            'virtual_initial_liquidity': True,
                            'fee_to_account_latest_known': owner,
                        },
                    },
                }

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            snapshot_inputs_projection_repository=FakeSnapshotInputsProjectionRepository(),
        )

        active_result = asyncio.run(read_model.enrich_positions(
            owner='chain-filter:owner-a',
            status='active',
            positions=[],
        ))
        closed_result = asyncio.run(read_model.enrich_positions(
            owner='chain-filter:owner-a',
            status='closed',
            positions=[],
        ))
        virtual_result = asyncio.run(read_model.enrich_positions(
            owner='chain-filter:owner-a',
            status='virtual',
            positions=[],
        ))

        self.assertEqual(active_result, [])
        self.assertEqual(closed_result, [])
        self.assertEqual(len(virtual_result), 1)
        self.assertEqual(virtual_result[0]['status'], 'virtual')


if __name__ == '__main__':
    unittest.main()
