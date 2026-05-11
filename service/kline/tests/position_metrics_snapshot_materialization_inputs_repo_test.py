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

    def test_build_fee_to_history_row_accepts_public_account_string(self):
        repository = PositionMetricsSnapshotMaterializationInputsRepository(connection=None)

        row = repository._build_fee_to_history_row(  # noqa: SLF001
            {
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction_id': 11,
                        'created_at': 1234,
                        'fee_to': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                    }
                },
                'source_chain_id': 'chain-src',
                'target_chain_id': 'chain-dst',
                'source_cert_hash': 'cert-1',
                'transaction_index': 3,
                'message_index': 4,
            }
        )

        self.assertEqual(row['fee_to_account'], '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee')
        self.assertEqual(row['created_at'], 1234)
        self.assertEqual(row['transaction_id'], 11)

    def test_build_fee_to_history_row_accepts_settled_owner_string(self):
        repository = PositionMetricsSnapshotMaterializationInputsRepository(connection=None)

        row = repository._build_fee_to_history_row(  # noqa: SLF001
            {
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction_id': 12,
                        'created_at_micros': 5678000,
                        'new_fee_to': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                    }
                },
                'source_chain_id': 'chain-src',
                'target_chain_id': 'chain-dst',
                'source_cert_hash': 'cert-2',
                'transaction_index': 5,
                'message_index': 6,
            }
        )

        self.assertEqual(row['fee_to_account'], '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee')
        self.assertEqual(row['created_at'], 5678)
        self.assertEqual(row['transaction_id'], 12)


if __name__ == '__main__':
    unittest.main()
