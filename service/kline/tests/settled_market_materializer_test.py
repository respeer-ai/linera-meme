import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.settled_market_materializer import SettledMarketMaterializer  # noqa: E402


class SettledMarketMaterializerTest(unittest.TestCase):
    class FakeMarketDeriver:
        def __init__(self):
            self.calls = []

        def derive_item(self, event, *, liquidity_semantics=None):
            self.calls.append((event, liquidity_semantics))
            output = {
                'settled_output_type': 'settled_liquidity_change',
                'settled_liquidity_change_id': f"liq-{event['normalized_event_id']}",
            }
            if liquidity_semantics is not None:
                output['liquidity_semantics'] = liquidity_semantics
            return {
                'normalized_event_id': event['normalized_event_id'],
                'settled_outputs': [output],
            }

        def derive_batch(self, events):
            return [self.derive_item(event) for event in events]

    class FakeClaimDeriver:
        def derive_item(self, event):
            return {
                'normalized_event_id': event['normalized_event_id'],
                'settled_outputs': [
                    {'settled_output_type': 'claim_balance_delta', 'claim_balance_delta_id': 'claim-1'},
                    {
                        'settled_output_type': 'claim_balance_diagnostic',
                        'claim_balance_diagnostic_id': 'diag-1',
                        'normalized_event_id': event['normalized_event_id'],
                    },
                ],
            }

    class FakeCorrelationDeriver:
        CORRELATION_DIAGNOSTIC = 'claim_delta_requires_new_transaction_correlation'

        def derive_batch(self, events):
            return {
                'outputs_by_event_id': {
                    'event-1': [
                        {
                            'settled_output_type': 'claim_balance_delta',
                            'claim_balance_delta_id': 'claim-correlated',
                            'normalized_event_id': 'event-1',
                            'derivation_source': 'correlated_swap_new_transaction',
                        }
                    ],
                },
                'batch_outputs': [],
                'resolved_event_ids': {'event-1'},
            }

        def filter_resolved_diagnostics(self, outputs, *, resolved_event_ids):
            return [
                output
                for output in outputs
                if output.get('settled_output_type') != 'claim_balance_diagnostic'
            ]

    class FakeTradeRepository:
        def __init__(self):
            self.trades = None

        def upsert_settled_trades(self, trades):
            self.trades = list(trades)

    class FakeLiquidityRepository:
        def __init__(self):
            self.changes = None

        def upsert_settled_liquidity_changes(self, changes):
            self.changes = list(changes)

    class FakeClaimBalanceRepository:
        def __init__(self):
            self.deltas = None
            self.diagnostics = None
            self.deleted_diagnostics = None
            self.deleted_correlated_deltas = None

        def delete_claim_balance_diagnostics_for_events(self, *, normalized_event_ids, diagnostic_types):
            self.deleted_diagnostics = (set(normalized_event_ids), set(diagnostic_types))

        def delete_correlated_claim_balance_deltas_for_events(self, *, normalized_event_ids):
            self.deleted_correlated_deltas = set(normalized_event_ids)

        def upsert_claim_balance_deltas(self, deltas):
            self.deltas = list(deltas)

        def upsert_claim_balance_diagnostics(self, diagnostics):
            self.diagnostics = list(diagnostics)

    def test_materialize_batch_persists_claim_outputs_to_claim_repository(self):
        trade_repository = self.FakeTradeRepository()
        liquidity_repository = self.FakeLiquidityRepository()
        claim_repository = self.FakeClaimBalanceRepository()
        materializer = SettledMarketMaterializer(
            settled_market_deriver=self.FakeMarketDeriver(),
            claim_balance_deriver=self.FakeClaimDeriver(),
            claim_balance_correlation_deriver=self.FakeCorrelationDeriver(),
            settled_trade_repository=trade_repository,
            settled_liquidity_change_repository=liquidity_repository,
            claim_balance_projection_repository=claim_repository,
        )

        materializer.materialize_batch([{'normalized_event_id': 'event-1'}])

        self.assertEqual(trade_repository.trades, [])
        self.assertEqual(liquidity_repository.changes, [{'settled_output_type': 'settled_liquidity_change', 'settled_liquidity_change_id': 'liq-event-1'}])
        self.assertEqual(
            claim_repository.deltas,
            [
                {'settled_output_type': 'claim_balance_delta', 'claim_balance_delta_id': 'claim-1'},
                {
                    'settled_output_type': 'claim_balance_delta',
                    'claim_balance_delta_id': 'claim-correlated',
                    'normalized_event_id': 'event-1',
                    'derivation_source': 'correlated_swap_new_transaction',
                },
            ],
        )
        self.assertEqual(
            claim_repository.deleted_diagnostics,
            (
                {'event-1'},
                {
                    'claim_delta_requires_new_transaction_correlation',
                    'ambiguous_new_transaction_correlation',
                    'missing_pool_token_metadata',
                },
            ),
        )
        self.assertEqual(claim_repository.deleted_correlated_deltas, {'event-1'})
        self.assertEqual(claim_repository.diagnostics, [])


    def test_materialize_batch_marks_initialize_liquidity_new_transaction_as_virtual(self):
        market_deriver = self.FakeMarketDeriver()
        trade_repository = self.FakeTradeRepository()
        liquidity_repository = self.FakeLiquidityRepository()
        materializer = SettledMarketMaterializer(
            settled_market_deriver=market_deriver,
            claim_balance_deriver=self.FakeClaimDeriver(),
            claim_balance_correlation_deriver=self.FakeCorrelationDeriver(),
            settled_trade_repository=trade_repository,
            settled_liquidity_change_repository=liquidity_repository,
        )
        initialize = {
            'normalized_event_id': 'event-initialize',
            'application_id': 'pool-app',
            'event_family': 'pool_initialize_liquidity_message_observed',
            'normalization_status': 'observed',
            'target_block_hash': 'initialize-block',
        }
        new_transaction = {
            'normalized_event_id': 'event-new-transaction',
            'application_id': 'pool-app',
            'event_family': 'pool_new_transaction_recorded',
            'normalization_status': 'observed',
            'source_cert_hash': 'initialize-block',
            'event_payload_json': {
                'decoded_payload_json': {
                    'transaction': {'transaction_type': 'AddLiquidity'},
                },
            },
        }

        materializer.materialize_batch([initialize, new_transaction])

        calls = {
            event['normalized_event_id']: semantics
            for event, semantics in market_deriver.calls
        }
        self.assertIsNone(calls['event-initialize'])
        self.assertEqual(calls['event-new-transaction'], 'virtual_initial_liquidity')
        self.assertIn(
            {
                'settled_output_type': 'settled_liquidity_change',
                'settled_liquidity_change_id': 'liq-event-new-transaction',
                'liquidity_semantics': 'virtual_initial_liquidity',
            },
            liquidity_repository.changes,
        )


    def test_materialize_batch_does_not_mark_non_add_liquidity_transaction_as_virtual(self):
        market_deriver = self.FakeMarketDeriver()
        materializer = SettledMarketMaterializer(
            settled_market_deriver=market_deriver,
            claim_balance_deriver=self.FakeClaimDeriver(),
            claim_balance_correlation_deriver=self.FakeCorrelationDeriver(),
            settled_trade_repository=self.FakeTradeRepository(),
            settled_liquidity_change_repository=self.FakeLiquidityRepository(),
        )
        initialize = {
            'normalized_event_id': 'event-initialize',
            'application_id': 'pool-app',
            'event_family': 'pool_initialize_liquidity_message_observed',
            'normalization_status': 'observed',
            'target_block_hash': 'initialize-block',
        }
        swap_transaction = {
            'normalized_event_id': 'event-swap-transaction',
            'application_id': 'pool-app',
            'event_family': 'pool_new_transaction_recorded',
            'normalization_status': 'observed',
            'source_cert_hash': 'initialize-block',
            'event_payload_json': {
                'decoded_payload_json': {
                    'transaction': {'transaction_type': 'BuyToken0'},
                },
            },
        }

        materializer.materialize_batch([initialize, swap_transaction])

        calls = {
            event['normalized_event_id']: semantics
            for event, semantics in market_deriver.calls
        }
        self.assertIsNone(calls['event-swap-transaction'])


if __name__ == '__main__':
    unittest.main()
