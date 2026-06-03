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
        def derive_item(self, event):
            return self.derive_batch([event])[0]

        def derive_batch(self, events):
            return [
                {
                    'normalized_event_id': 'event-1',
                    'settled_outputs': [
                        {'settled_output_type': 'settled_trade', 'settled_trade_id': 'trade-1'},
                        {'settled_output_type': 'settled_liquidity_change', 'settled_liquidity_change_id': 'liq-1'},
                    ],
                }
                for _event in events
            ]

    class FakeClaimDeriver:
        def derive_item(self, event):
            return {
                'normalized_event_id': event['normalized_event_id'],
                'settled_outputs': [
                    {'settled_output_type': 'claim_balance_delta', 'claim_balance_delta_id': 'claim-1'},
                    {'settled_output_type': 'claim_balance_diagnostic', 'claim_balance_diagnostic_id': 'diag-1'},
                ],
            }

    class FakeCorrelationDeriver:
        def derive_batch(self, events):
            return {
                'outputs_by_event_id': {
                    'event-1': [
                        {
                            'settled_output_type': 'claim_balance_delta',
                            'claim_balance_delta_id': 'claim-correlated',
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

        self.assertEqual(trade_repository.trades, [{'settled_output_type': 'settled_trade', 'settled_trade_id': 'trade-1'}])
        self.assertEqual(liquidity_repository.changes, [{'settled_output_type': 'settled_liquidity_change', 'settled_liquidity_change_id': 'liq-1'}])
        self.assertEqual(
            claim_repository.deltas,
            [
                {'settled_output_type': 'claim_balance_delta', 'claim_balance_delta_id': 'claim-1'},
                {'settled_output_type': 'claim_balance_delta', 'claim_balance_delta_id': 'claim-correlated'},
            ],
        )
        self.assertEqual(claim_repository.diagnostics, [])


if __name__ == '__main__':
    unittest.main()
