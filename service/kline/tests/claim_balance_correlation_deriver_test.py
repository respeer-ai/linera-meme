import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.claim_balance_correlation_deriver import ClaimBalanceCorrelationDeriver  # noqa: E402


class ClaimBalanceCorrelationDeriverTest(unittest.TestCase):
    class FakePoolCatalogRepository:
        def list_current_pools(self):
            return [
                {
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@pool-chain',
                    'token_0': 'token-0',
                    'token_1': 'TLINERA',
                }
            ]

    class FakeNormalizedEventRepository:
        def __init__(self, *, messages=None, new_transactions=None):
            self.messages = list(messages or [])
            self.new_transactions = list(new_transactions or [])

        def list_correlatable_pool_messages(self, *, application_id, target_block_hash):
            return [
                message
                for message in self.messages
                if message.get('application_id') == application_id
                and message.get('target_block_hash') == target_block_hash
            ]

        def list_pool_new_transactions_for_source_block(self, *, application_id, source_cert_hash):
            return [
                new_transaction
                for new_transaction in self.new_transactions
                if new_transaction.get('application_id') == application_id
                and new_transaction.get('source_cert_hash') == source_cert_hash
            ]

    def account(self, chain='user-chain', owner='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'):
        return {
            'chain_id': chain,
            'owner': f'0x{owner}',
        }

    def pool_event(self, message_type, payload, *, event_id=None, block_hash='source-block'):
        decoded_payload = dict(payload)
        decoded_payload['message_type'] = message_type
        return {
            'normalized_event_id': event_id or f'event-{message_type}',
            'raw_fact_id': '10',
            'raw_table': 'raw_posted_messages',
            'application_id': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            'payload_kind': 'message',
            'event_family': f'pool_{message_type}_message_observed',
            'event_type': message_type,
            'correlation_key': f'pool:key:{message_type}',
            'normalization_status': 'observed',
            'target_chain_id': 'pool-chain',
            'target_block_hash': block_hash,
            'transaction_index': 2,
            'message_index': 3,
            'event_payload_json': {
                'decoded_payload_json': decoded_payload,
            },
        }

    def new_transaction(self, transaction, *, source_cert_hash='source-block', event_id='event-new-transaction'):
        return self.pool_event(
            'new_transaction',
            {'transaction': transaction},
            event_id=event_id,
            block_hash='target-block',
        ) | {
            'event_family': 'pool_new_transaction_recorded',
            'source_cert_hash': source_cert_hash,
            'target_block_hash': 'target-block',
        }

    def test_correlates_swap_to_new_transaction_and_credits_recipient_output(self):
        swap = self.pool_event('swap', {
            'origin': self.account(),
            'amount_0_in': None,
            'amount_1_in': '50',
            'amount_0_out_min': '10',
            'amount_1_out_min': None,
            'to': self.account(chain='recipient-chain', owner='cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'),
        })
        new_transaction = self.new_transaction({
            'transaction_id': 1,
            'transaction_type': 'BuyToken0',
            'from': self.account(),
            'amount_0_out': '12',
            'amount_1_in': '50',
        })

        result = ClaimBalanceCorrelationDeriver(
            pool_catalog_repository=self.FakePoolCatalogRepository(),
        ).derive_batch([swap, new_transaction])

        outputs = result['outputs_by_event_id']['event-swap']
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]['derivation_source'], 'correlated_swap_new_transaction')
        self.assertEqual(outputs[0]['token'], 'token-0')
        self.assertEqual(outputs[0]['owner'], '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc@recipient-chain')
        self.assertEqual(outputs[0]['delta_amount'], '12')
        self.assertEqual(outputs[0]['delta_direction'], 'credit')
        self.assertEqual(outputs[0]['derivation_confidence'], 'exact')
        self.assertIn('event-swap', result['resolved_event_ids'])

    def test_correlates_add_liquidity_to_new_transaction_and_credits_excess_inputs(self):
        add_liquidity = self.pool_event('add_liquidity', {
            'origin': self.account(),
            'amount_0_in': '100',
            'amount_1_in': '90',
            'amount_0_out_min': None,
            'amount_1_out_min': None,
            'to': None,
        })
        new_transaction = self.new_transaction({
            'transaction_id': 2,
            'transaction_type': 'AddLiquidity',
            'from': self.account(),
            'amount_0_in': '80',
            'amount_1_in': '90',
            'liquidity': '20',
        })

        result = ClaimBalanceCorrelationDeriver(
            pool_catalog_repository=self.FakePoolCatalogRepository(),
        ).derive_batch([add_liquidity, new_transaction])

        outputs = result['outputs_by_event_id']['event-add_liquidity']
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]['derivation_source'], 'correlated_add_liquidity_new_transaction')
        self.assertEqual(outputs[0]['token'], 'token-0')
        self.assertEqual(outputs[0]['delta_amount'], '20')

    def test_correlates_remove_liquidity_to_new_transaction_and_credits_outputs(self):
        remove_liquidity = self.pool_event('remove_liquidity', {
            'origin': self.account(),
            'liquidity': '7',
            'amount_0_out_min': '10',
            'amount_1_out_min': '5',
            'to': None,
        })
        new_transaction = self.new_transaction({
            'transaction_id': 3,
            'transaction_type': 'RemoveLiquidity',
            'from': self.account(),
            'amount_0_out': '11',
            'amount_1_out': '6',
            'liquidity': '7',
        })

        result = ClaimBalanceCorrelationDeriver(
            pool_catalog_repository=self.FakePoolCatalogRepository(),
        ).derive_batch([remove_liquidity, new_transaction])

        outputs = result['outputs_by_event_id']['event-remove_liquidity']
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0]['derivation_source'], 'correlated_remove_liquidity_new_transaction')
        self.assertEqual(outputs[0]['token'], 'token-0')
        self.assertEqual(outputs[0]['delta_amount'], '11')
        self.assertEqual(outputs[1]['token'], 'native')
        self.assertEqual(outputs[1]['delta_amount'], '6')

    def test_missing_pool_token_metadata_keeps_partial_diagnostic(self):
        swap = self.pool_event('swap', {
            'origin': self.account(),
            'amount_0_in': None,
            'amount_1_in': '50',
            'to': None,
        })
        new_transaction = self.new_transaction({
            'transaction_type': 'BuyToken0',
            'from': self.account(),
            'amount_0_out': '12',
            'amount_1_in': '50',
        })

        result = ClaimBalanceCorrelationDeriver().derive_batch([swap, new_transaction])

        outputs = result['outputs_by_event_id']['event-swap']
        self.assertEqual(outputs[0]['settled_output_type'], 'claim_balance_diagnostic')
        self.assertEqual(outputs[0]['diagnostic_type'], 'missing_pool_token_metadata')
        self.assertEqual(outputs[0]['derivation_confidence'], 'partial')

    def test_correlates_message_with_repository_new_transaction(self):
        swap = self.pool_event('swap', {
            'origin': self.account(),
            'amount_0_in': None,
            'amount_1_in': '50',
            'to': None,
        })
        new_transaction = self.new_transaction({
            'transaction_type': 'BuyToken0',
            'from': self.account(),
            'amount_0_out': '12',
            'amount_1_in': '50',
        })

        result = ClaimBalanceCorrelationDeriver(
            pool_catalog_repository=self.FakePoolCatalogRepository(),
            normalized_event_repository=self.FakeNormalizedEventRepository(
                new_transactions=[new_transaction],
            ),
        ).derive_batch([swap])

        outputs = result['outputs_by_event_id']['event-swap']
        self.assertEqual(outputs[0]['derivation_source'], 'correlated_swap_new_transaction')
        self.assertEqual(outputs[0]['delta_amount'], '12')

    def test_correlates_repository_message_with_new_transaction_batch_event(self):
        swap = self.pool_event('swap', {
            'origin': self.account(),
            'amount_0_in': None,
            'amount_1_in': '50',
            'to': None,
        })
        new_transaction = self.new_transaction({
            'transaction_type': 'BuyToken0',
            'from': self.account(),
            'amount_0_out': '12',
            'amount_1_in': '50',
        })

        result = ClaimBalanceCorrelationDeriver(
            pool_catalog_repository=self.FakePoolCatalogRepository(),
            normalized_event_repository=self.FakeNormalizedEventRepository(messages=[swap]),
        ).derive_batch([new_transaction])

        self.assertEqual(result['outputs_by_event_id'], {})
        self.assertEqual(len(result['batch_outputs']), 1)
        self.assertEqual(result['batch_outputs'][0]['derivation_source'], 'correlated_swap_new_transaction')
        self.assertEqual(result['batch_outputs'][0]['delta_amount'], '12')

    def test_ambiguous_new_transaction_match_is_diagnostic_only(self):
        swap = self.pool_event('swap', {
            'origin': self.account(),
            'amount_0_in': None,
            'amount_1_in': '50',
            'to': None,
        })
        first = self.new_transaction(
            {'transaction_type': 'BuyToken0', 'from': self.account(), 'amount_0_out': '12', 'amount_1_in': '50'},
            event_id='new-1',
        )
        second = self.new_transaction(
            {'transaction_type': 'BuyToken0', 'from': self.account(), 'amount_0_out': '13', 'amount_1_in': '50'},
            event_id='new-2',
        )

        result = ClaimBalanceCorrelationDeriver(
            pool_catalog_repository=self.FakePoolCatalogRepository(),
        ).derive_batch([swap, first, second])

        outputs = result['outputs_by_event_id']['event-swap']
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]['settled_output_type'], 'claim_balance_diagnostic')
        self.assertEqual(outputs[0]['diagnostic_type'], 'ambiguous_new_transaction_correlation')


if __name__ == '__main__':
    unittest.main()
