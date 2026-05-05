import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.position_metrics_snapshot_materialization_inputs_repo import PositionMetricsSnapshotMaterializationInputsRepository  # noqa: E402


class PositionMetricsSnapshotMaterializationInputsRepositoryTest(unittest.TestCase):
    def test_build_fee_to_history_row_accepts_public_account_string(self):
        repository = PositionMetricsSnapshotMaterializationInputsRepository(connection=None)

        row = repository._build_fee_to_history_row(  # noqa: SLF001
            {
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction_id': 11,
                        'created_at': 1234,
                        'fee_to': 'chain-fee:owner-fee',
                    }
                },
                'source_chain_id': 'chain-src',
                'target_chain_id': 'chain-dst',
                'source_cert_hash': 'cert-1',
                'transaction_index': 3,
                'message_index': 4,
            }
        )

        self.assertEqual(row['fee_to_account'], 'chain-fee:owner-fee')
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
                        'new_fee_to': 'owner-fee@chain-fee',
                    }
                },
                'source_chain_id': 'chain-src',
                'target_chain_id': 'chain-dst',
                'source_cert_hash': 'cert-2',
                'transaction_index': 5,
                'message_index': 6,
            }
        )

        self.assertEqual(row['fee_to_account'], 'chain-fee:owner-fee')
        self.assertEqual(row['created_at'], 5678)
        self.assertEqual(row['transaction_id'], 12)


if __name__ == '__main__':
    unittest.main()
