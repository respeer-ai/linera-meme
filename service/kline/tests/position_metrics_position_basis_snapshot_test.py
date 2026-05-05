import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_position_basis_snapshot import (  # noqa: E402
    PositionMetricsPositionBasisSnapshot,
)
from query.read_models.position_metrics_snapshot_semantic_facts import (  # noqa: E402
    PositionMetricsSnapshotSemanticFacts,
)


class PositionMetricsPositionBasisSnapshotTest(unittest.TestCase):
    def test_exposes_named_position_basis_fields(self):
        snapshot = PositionMetricsPositionBasisSnapshot(
            {
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 11,
                'basis_time_ms': 1200,
                'semantic_facts': {
                    'prior_liquidity_before_basis': '0',
                    'post_basis_remove_count': 1,
                },
            }
        )

        self.assertEqual(snapshot.status(), 'active')
        self.assertEqual(snapshot.basis_type(), 'add_liquidity')
        self.assertEqual(snapshot.current_liquidity(), '10')
        self.assertEqual(snapshot.basis_transaction_id(), 11)
        self.assertEqual(snapshot.basis_time_ms(), 1200)
        self.assertEqual(snapshot.prior_liquidity_before_basis(), '0')
        self.assertEqual(snapshot.post_basis_remove_count(), 1)
        self.assertEqual(snapshot.semantic_facts().get('prior_liquidity_before_basis'), '0')
        self.assertTrue(snapshot.semantic_facts().has('prior_liquidity_before_basis'))
        self.assertEqual(
            snapshot.shadow_latest_dict(),
            {
                'latest_position_transaction_id': 11,
                'latest_position_created_at': 1200,
            },
        )
        self.assertEqual(
            snapshot.summary_dict(),
            {
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 11,
                'basis_time_ms': 1200,
                'basis_opens_current_round': False,
                'has_only_zero_liquidity_before_basis': False,
                'current_round_liquidity_event_count': None,
                'current_round_started_at': None,
                'current_round_started_transaction_id': None,
                'current_round_trade_count_before_basis': None,
                'trade_count_between_basis_and_fee_free_basis': None,
                'exact_current_principal_case': None,
                'protocol_fee_liquidity_provenance_case': None,
                'basis_protocol_fee_liquidity_minted': None,
                'post_basis_protocol_fee_liquidity_minted': None,
                'post_basis_protocol_fee_mint_event_count': None,
                'post_basis_protocol_fee_liquidity_minted_before_first_add': None,
                'fee_to_continuous_protocol_fee_liquidity_current': None,
                'protocol_fee_current_owner_provenance_case': None,
                'basis_protocol_fee_liquidity_owned_by_current_owner': None,
                'post_basis_protocol_fee_liquidity_owned_by_current_owner': None,
                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': None,
                'protocol_fee_liquidity_owned_by_current_owner_current': None,
                'protocol_fee_liquidity_owned_by_other_accounts': None,
                'protocol_fee_liquidity_owner_unknown': None,
                'fee_to_continuity_case': None,
                'fee_to_continuity_change_count_after_basis': None,
                'fee_to_continuity_known_before_basis': None,
                'fee_to_continuity_owner': None,
                'fee_to_account_at_basis': None,
                'fee_to_account_latest_known': None,
            },
        )
        self.assertEqual(
            snapshot.raw(),
            {
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 11,
                'basis_time_ms': 1200,
                'semantic_facts': {
                    'prior_liquidity_before_basis': '0',
                    'post_basis_remove_count': 1,
                },
            },
        )

    def test_projects_semantic_facts_from_state_payload(self):
        facts = PositionMetricsSnapshotSemanticFacts.from_state_payload(
            {
                'prior_liquidity_before_basis': '0',
                'current_round_started_at': 1000,
                'exact_current_principal': {
                    'exact_current_principal_case': 'exact_case',
                    'post_basis_remove_count': 2,
                },
                'fee_to_continuity': {
                    'continuity_case': 'continuous',
                    'fee_to_account_latest_known': 'chain:owner-a',
                },
            }
        )

        self.assertEqual(facts.get('prior_liquidity_before_basis'), '0')
        self.assertEqual(facts.current_round_started_at(), 1000)
        self.assertEqual(facts.exact_current_principal_case(), 'exact_case')
        self.assertEqual(facts.post_basis_remove_count(), 2)
        self.assertEqual(facts.fee_to_continuity_case(), 'continuous')
        self.assertEqual(facts.fee_to_account_latest_known(), 'chain:owner-a')
