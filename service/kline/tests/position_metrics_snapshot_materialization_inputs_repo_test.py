import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.position_metrics_snapshot_materialization_inputs_repo import PositionMetricsSnapshotMaterializationInputsRepository  # noqa: E402


class PositionMetricsSnapshotMaterializationInputsRepositoryTest(unittest.TestCase):
    class FakePoolHistoryRepository:
        def __init__(self):
            self.requests = []

        def get_pool_transaction_history(self, *, pool_application, pool_id):
            self.requests.append({
                'pool_application': pool_application,
                'pool_id': pool_id,
            })
            return [{'transaction_id': 1}]

    def test_list_pool_transaction_history_requires_canonical_pool_application(self):
        pool_history_repository = self.FakePoolHistoryRepository()
        repository = PositionMetricsSnapshotMaterializationInputsRepository(
            connection=None,
            settled_trade_projection_repo=object(),
            settled_liquidity_projection_repo=object(),
            settled_pool_history_projection_repo=pool_history_repository,
        )

        rows = repository.list_pool_transaction_history(
            pool_application_id='0x095554fa3074f0b9371097a490882d6aeb562612141a7731dfd24cadf30b7484@b87827a42fa7bb6d129940a5dc02bb51e3bff57f2457306d9095872c3b7ed9f6',
            pool_chain_id='b87827a42fa7bb6d129940a5dc02bb51e3bff57f2457306d9095872c3b7ed9f6',
        )

        self.assertEqual(rows, [{'transaction_id': 1}])
        self.assertEqual(
            pool_history_repository.requests,
            [{
                'pool_application': '0x095554fa3074f0b9371097a490882d6aeb562612141a7731dfd24cadf30b7484@b87827a42fa7bb6d129940a5dc02bb51e3bff57f2457306d9095872c3b7ed9f6',
                'pool_id': None,
            }],
        )


    def test_fresh_cursor_returns_dictionary_cursor(self):
        class FakeConnection:
            def __init__(self):
                self.requests = []

            def cursor(self, dictionary=False):
                self.requests.append(dictionary)
                return {'dictionary': dictionary}

        connection = FakeConnection()
        repository = PositionMetricsSnapshotMaterializationInputsRepository(connection=connection)

        cursor = repository.fresh_cursor(dictionary=True)

        self.assertEqual(cursor, {'dictionary': True})
        self.assertEqual(connection.requests, [True, True])

    def test_get_pool_created_metadata_prefers_pool_catalog_creator(self):
        class FakeCursor:
            def __init__(self):
                self.requests = []

            def execute(self, sql, params=()):
                self.requests.append((" ".join(sql.split()), params))

            def fetchone(self):
                return {
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-pool',
                    'token_0': 'AAA',
                    'token_1': 'TLINERA',
                    'creator_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-owner',
                    'event_family': 'swap_pool_created_recorded',
                    'source_event_key': 'event-1',
                }

            def close(self):
                return None

        class FakeConnection:
            def __init__(self):
                self.cursor_obj = FakeCursor()

            def cursor(self, dictionary=False):
                self.dictionary = dictionary
                return self.cursor_obj

        connection = FakeConnection()
        repository = PositionMetricsSnapshotMaterializationInputsRepository(connection=connection)

        metadata = repository.get_pool_created_metadata(
            pool_application_id='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-pool',
        )

        self.assertEqual(
            metadata,
            {
                'event_family': 'swap_pool_created_recorded',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-pool',
                'token_0': 'AAA',
                'token_1': 'TLINERA',
                'creator_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-owner',
                'source_event_key': 'event-1',
                'source': 'pool_catalog_v2',
            },
        )
        self.assertIn('FROM pool_catalog_v2', connection.cursor_obj.requests[0][0])
        self.assertEqual(
            connection.cursor_obj.requests[0][1],
            ('0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-pool',),
        )


    def test_list_active_position_owners_for_pool_delegates_to_liquidity_projection(self):
        class FakeLiquidityProjectionRepository:
            def __init__(self):
                self.calls = []

            def list_active_position_owners_for_pool(self, **kwargs):
                self.calls.append(dict(kwargs))
                return ['owner-a@chain']

        liquidity_repository = FakeLiquidityProjectionRepository()
        repository = PositionMetricsSnapshotMaterializationInputsRepository(
            connection=None,
            settled_liquidity_projection_repo=liquidity_repository,
        )

        owners = repository.list_active_position_owners_for_pool(pool_application='pool@app')

        self.assertEqual(owners, ['owner-a@chain'])
        self.assertEqual(liquidity_repository.calls, [{'pool_application': 'pool@app'}])


if __name__ == '__main__':
    unittest.main()
