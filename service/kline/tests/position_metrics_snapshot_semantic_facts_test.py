import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_snapshot_semantic_facts import (  # noqa: E402
    PositionMetricsSnapshotSemanticFacts,
)


class PositionMetricsSnapshotSemanticFactsTest(unittest.TestCase):
    def test_exposes_lookup_contract(self):
        facts = PositionMetricsSnapshotSemanticFacts(
            {
                'prior_liquidity_before_basis': '0',
                'basis_opens_current_round': True,
                'has_only_zero_liquidity_before_basis': False,
                'current_round_liquidity_event_count': '3',
                'current_round_started_at': '1000',
                'current_round_started_transaction_id': '10',
                'current_round_trade_count_before_basis': '2',
                'trade_count_between_basis_and_fee_free_basis': '1',
                'exact_current_principal_case': 'post_basis_swaps_without_liquidity_changes',
                'protocol_fee_liquidity_provenance_case': 'basis_only_mints',
                'protocol_fee_current_owner_provenance_case': 'all_mints_owned_by_current_owner',
                'basis_protocol_fee_liquidity_minted': '2',
                'post_basis_protocol_fee_liquidity_minted': '3',
                'post_basis_protocol_fee_mint_event_count': '1',
                'post_basis_protocol_fee_liquidity_minted_before_first_add': '3',
                'fee_to_continuous_protocol_fee_liquidity_current': '5',
                'basis_protocol_fee_liquidity_owned_by_current_owner': '2',
                'post_basis_protocol_fee_liquidity_owned_by_current_owner': '3',
                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '3',
                'protocol_fee_liquidity_owned_by_current_owner_current': '5',
                'protocol_fee_liquidity_owned_by_other_accounts': '0',
                'protocol_fee_liquidity_owner_unknown': '0',
                'full_protocol_fee_liquidity_owned_by_current_owner': '15',
                'full_protocol_fee_liquidity_owned_by_other_accounts': '0',
                'full_protocol_fee_liquidity_owner_unknown': '0',
                'full_protocol_fee_current_owner_provenance_case': 'all_mints_owned_by_current_owner',
                'fee_to_continuity_case': 'continuous_no_changes_after_basis',
                'fee_to_continuity_change_count_after_basis': '2',
                'fee_to_continuity_known_before_basis': False,
                'fee_to_continuity_owner': 'chain:owner-a',
                'fee_to_account_at_basis': 'chain:owner-a',
                'fee_to_account_latest_known': 'chain:owner-b',
            }
        )

        self.assertEqual(
            facts.raw(),
            {
                'prior_liquidity_before_basis': '0',
                'basis_opens_current_round': True,
                'has_only_zero_liquidity_before_basis': False,
                'current_round_liquidity_event_count': '3',
                'current_round_started_at': '1000',
                'current_round_started_transaction_id': '10',
                'current_round_trade_count_before_basis': '2',
                'trade_count_between_basis_and_fee_free_basis': '1',
                'exact_current_principal_case': 'post_basis_swaps_without_liquidity_changes',
                'protocol_fee_liquidity_provenance_case': 'basis_only_mints',
                'protocol_fee_current_owner_provenance_case': 'all_mints_owned_by_current_owner',
                'basis_protocol_fee_liquidity_minted': '2',
                'post_basis_protocol_fee_liquidity_minted': '3',
                'post_basis_protocol_fee_mint_event_count': '1',
                'post_basis_protocol_fee_liquidity_minted_before_first_add': '3',
                'fee_to_continuous_protocol_fee_liquidity_current': '5',
                'basis_protocol_fee_liquidity_owned_by_current_owner': '2',
                'post_basis_protocol_fee_liquidity_owned_by_current_owner': '3',
                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '3',
                'protocol_fee_liquidity_owned_by_current_owner_current': '5',
                'protocol_fee_liquidity_owned_by_other_accounts': '0',
                'protocol_fee_liquidity_owner_unknown': '0',
                'full_protocol_fee_liquidity_owned_by_current_owner': '15',
                'full_protocol_fee_liquidity_owned_by_other_accounts': '0',
                'full_protocol_fee_liquidity_owner_unknown': '0',
                'full_protocol_fee_current_owner_provenance_case': 'all_mints_owned_by_current_owner',
                'fee_to_continuity_case': 'continuous_no_changes_after_basis',
                'fee_to_continuity_change_count_after_basis': '2',
                'fee_to_continuity_known_before_basis': False,
                'fee_to_continuity_owner': 'chain:owner-a',
                'fee_to_account_at_basis': 'chain:owner-a',
                'fee_to_account_latest_known': 'chain:owner-b',
            },
        )
        self.assertEqual(facts.get('prior_liquidity_before_basis'), '0')
        self.assertIsNone(facts.get('missing'))
        self.assertTrue(facts.has('fee_to_continuity_known_before_basis'))
        self.assertFalse(facts.has('missing'))
        self.assertTrue(facts.basis_opens_current_round())
        self.assertFalse(facts.has_only_zero_liquidity_before_basis())
        self.assertEqual(facts.current_round_liquidity_event_count(), 3)
        self.assertEqual(facts.current_round_started_at(), 1000)
        self.assertEqual(facts.current_round_started_transaction_id(), 10)
        self.assertEqual(facts.current_round_trade_count_before_basis(), 2)
        self.assertEqual(facts.trade_count_between_basis_and_fee_free_basis(), 1)
        self.assertEqual(facts.exact_current_principal_case(), 'post_basis_swaps_without_liquidity_changes')
        self.assertEqual(facts.protocol_fee_liquidity_provenance_case(), 'basis_only_mints')
        self.assertEqual(facts.protocol_fee_current_owner_provenance_case(), 'all_mints_owned_by_current_owner')
        self.assertEqual(facts.basis_protocol_fee_liquidity_minted(), '2')
        self.assertEqual(facts.post_basis_protocol_fee_liquidity_minted(), '3')
        self.assertEqual(facts.post_basis_protocol_fee_mint_event_count(), 1)
        self.assertEqual(facts.post_basis_protocol_fee_liquidity_minted_before_first_add(), '3')
        self.assertEqual(facts.fee_to_continuous_protocol_fee_liquidity_current(), '5')
        self.assertEqual(facts.basis_protocol_fee_liquidity_owned_by_current_owner(), '2')
        self.assertEqual(facts.post_basis_protocol_fee_liquidity_owned_by_current_owner(), '3')
        self.assertEqual(facts.post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add(), '3')
        self.assertEqual(facts.protocol_fee_liquidity_owned_by_current_owner_current(), '5')
        self.assertEqual(facts.protocol_fee_liquidity_owned_by_other_accounts(), '0')
        self.assertEqual(facts.protocol_fee_liquidity_owner_unknown(), '0')
        self.assertEqual(facts.full_protocol_fee_liquidity_owned_by_current_owner(), '15')
        self.assertEqual(facts.full_protocol_fee_liquidity_owned_by_other_accounts(), '0')
        self.assertEqual(facts.full_protocol_fee_liquidity_owner_unknown(), '0')
        self.assertEqual(facts.full_protocol_fee_current_owner_provenance_case(), 'all_mints_owned_by_current_owner')
        self.assertEqual(facts.fee_to_continuity_case(), 'continuous_no_changes_after_basis')
        self.assertEqual(facts.fee_to_continuity_change_count_after_basis(), 2)
        self.assertFalse(facts.fee_to_continuity_known_before_basis())
        self.assertEqual(facts.fee_to_continuity_owner(), 'chain:owner-a')
        self.assertEqual(facts.fee_to_account_at_basis(), 'chain:owner-a')
        self.assertEqual(facts.fee_to_account_latest_known(), 'chain:owner-b')

    def test_handles_missing_payload(self):
        facts = PositionMetricsSnapshotSemanticFacts(None)

        self.assertEqual(facts.raw(), {})
        self.assertIsNone(facts.get('prior_liquidity_before_basis'))
        self.assertFalse(facts.has('prior_liquidity_before_basis'))
        self.assertFalse(facts.basis_opens_current_round())
        self.assertFalse(facts.has_only_zero_liquidity_before_basis())
        self.assertIsNone(facts.current_round_liquidity_event_count())
        self.assertIsNone(facts.current_round_started_at())
        self.assertIsNone(facts.current_round_started_transaction_id())
        self.assertIsNone(facts.current_round_trade_count_before_basis())
        self.assertIsNone(facts.trade_count_between_basis_and_fee_free_basis())
        self.assertIsNone(facts.exact_current_principal_case())
        self.assertIsNone(facts.protocol_fee_liquidity_provenance_case())
        self.assertIsNone(facts.protocol_fee_current_owner_provenance_case())
        self.assertIsNone(facts.basis_protocol_fee_liquidity_minted())
        self.assertIsNone(facts.post_basis_protocol_fee_liquidity_minted())
        self.assertIsNone(facts.post_basis_protocol_fee_mint_event_count())
        self.assertIsNone(facts.post_basis_protocol_fee_liquidity_minted_before_first_add())
        self.assertIsNone(facts.fee_to_continuous_protocol_fee_liquidity_current())
        self.assertIsNone(facts.basis_protocol_fee_liquidity_owned_by_current_owner())
        self.assertIsNone(facts.post_basis_protocol_fee_liquidity_owned_by_current_owner())
        self.assertIsNone(facts.post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add())
        self.assertIsNone(facts.protocol_fee_liquidity_owned_by_current_owner_current())
        self.assertIsNone(facts.protocol_fee_liquidity_owned_by_other_accounts())
        self.assertIsNone(facts.protocol_fee_liquidity_owner_unknown())
        self.assertIsNone(facts.fee_to_continuity_case())
        self.assertIsNone(facts.fee_to_continuity_change_count_after_basis())
        self.assertIsNone(facts.fee_to_continuity_known_before_basis())
        self.assertIsNone(facts.fee_to_continuity_owner())
        self.assertIsNone(facts.fee_to_account_at_basis())
        self.assertIsNone(facts.fee_to_account_latest_known())


if __name__ == '__main__':
    unittest.main()
