import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.claim_balance_deriver import ClaimBalanceDeriver  # noqa: E402


class ClaimBalanceDeriverTest(unittest.TestCase):
    def base_event(self, message_type, decoded_payload):
        payload = dict(decoded_payload)
        payload['message_type'] = message_type
        return {
            'normalized_event_id': f'event-{message_type}',
            'application_id': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            'event_family': f'pool_{message_type}_recorded',
            'normalization_status': 'observed',
            'target_chain_id': 'pool-chain',
            'target_block_hash': 'block-1',
            'target_block_height': 7,
            'transaction_index': 2,
            'message_index': 3,
            'event_payload_json': {
                'decoded_payload_json': payload,
            },
        }

    def account(self, chain='user-chain', owner='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'):
        return {
            'chain_id': chain,
            'owner': f'0x{owner}',
        }

    def test_claim_derives_claimable_debit_and_fungible_claiming_credit(self):
        event = self.base_event('claim', {
            'origin': self.account(),
            'token': 'token-app',
            'amount': '13',
        })

        derived = ClaimBalanceDeriver().derive_item(event)

        self.assertEqual(derived['derivation_status'], 'settled')
        outputs = derived['settled_outputs']
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0]['balance_kind'], 'claimable')
        self.assertEqual(outputs[0]['delta_direction'], 'debit')
        self.assertEqual(outputs[0]['owner'], '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@user-chain')
        self.assertEqual(outputs[0]['pool_application_id'], '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@pool-chain')
        self.assertEqual(outputs[1]['balance_kind'], 'claiming')
        self.assertEqual(outputs[1]['delta_direction'], 'credit')

    def test_native_claim_derives_only_claimable_debit(self):
        event = self.base_event('claim', {
            'origin': self.account(),
            'token': None,
            'amount': '5',
        })

        outputs = ClaimBalanceDeriver().derive_item(event)['settled_outputs']

        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]['token'], 'native')
        self.assertEqual(outputs[0]['balance_kind'], 'claimable')

    def test_claim_transfer_receipt_success_derives_claiming_debit(self):
        event = self.base_event('claim_transfer_receipt', {
            'receipt': {
                'owner': self.account(),
                'token': 'token-app',
                'amount': '7',
                'result': {'ok': None},
            }
        })

        outputs = ClaimBalanceDeriver().derive_item(event)['settled_outputs']

        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]['balance_kind'], 'claiming')
        self.assertEqual(outputs[0]['delta_direction'], 'debit')
        self.assertEqual(outputs[0]['derivation_source'], 'claim_transfer_receipt')

    def test_claim_transfer_receipt_failure_recredits_claimable(self):
        event = self.base_event('claim_transfer_receipt', {
            'receipt': {
                'owner': self.account(),
                'token': 'token-app',
                'amount': '7',
                'result': {'err': 'failed'},
            }
        })

        outputs = ClaimBalanceDeriver().derive_item(event)['settled_outputs']

        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0]['balance_kind'], 'claiming')
        self.assertEqual(outputs[0]['delta_direction'], 'debit')
        self.assertEqual(outputs[1]['balance_kind'], 'claimable')
        self.assertEqual(outputs[1]['delta_direction'], 'credit')

    def test_fund_result_add_liquidity_failure_credits_prev(self):
        event = self.base_event('fund_result', {
            'prev': {
                'from': self.account(),
                'token': 'token-app',
                'amount_in': '11',
            },
            'request': {'fund_type': 'AddLiquidity'},
            'result': {'err': 'failed'},
        })

        outputs = ClaimBalanceDeriver().derive_item(event)['settled_outputs']

        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]['balance_kind'], 'claimable')
        self.assertEqual(outputs[0]['delta_direction'], 'credit')
        self.assertEqual(outputs[0]['delta_amount'], '11')
        self.assertEqual(outputs[0]['derivation_source'], 'fund_result')

    def test_add_liquidity_transfer_receipt_failure_credits_prev(self):
        event = self.base_event('add_liquidity_transfer_receipt', {
            'receipt': {
                'prev': {
                    'from': self.account(),
                    'token': 'token-app',
                    'amount_in': '17',
                },
                'result': {'err': 'failed'},
            }
        })

        outputs = ClaimBalanceDeriver().derive_item(event)['settled_outputs']

        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]['delta_amount'], '17')
        self.assertEqual(outputs[0]['derivation_source'], 'add_liquidity_transfer_receipt')

    def test_swap_transfer_receipt_failure_derives_diagnostic_only(self):
        event = self.base_event('swap_transfer_receipt', {
            'receipt': {
                'result': {'err': 'failed'},
            }
        })

        outputs = ClaimBalanceDeriver().derive_item(event)['settled_outputs']

        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]['settled_output_type'], 'claim_balance_diagnostic')
        self.assertEqual(outputs[0]['diagnostic_type'], 'swap_transfer_receipt_failure_has_no_claim_delta')

    def test_observed_swap_message_does_not_emit_partial_correlation_diagnostic(self):
        event = self.base_event('swap', {
            'origin': self.account(),
            'amount_0_in': None,
            'amount_1_in': '9',
            'to': None,
        })

        outputs = ClaimBalanceDeriver().derive_item(event)['settled_outputs']

        self.assertEqual(outputs, [])

    def test_rejected_claim_message_derives_no_handler_delta_diagnostic(self):
        event = self.base_event('claim', {
            'origin': self.account(),
            'token': 'token-app',
            'amount': '13',
        })
        event['normalization_status'] = 'rejected'
        event['event_payload_json']['rejected'] = True

        outputs = ClaimBalanceDeriver().derive_item(event)['settled_outputs']

        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]['settled_output_type'], 'claim_balance_diagnostic')
        self.assertEqual(outputs[0]['diagnostic_type'], 'rejected_message_no_handler_delta')
        self.assertEqual(outputs[0]['derivation_source'], 'claim')
        self.assertEqual(outputs[0]['derivation_confidence'], 'exact')
        self.assertTrue(outputs[0]['rejected'])


if __name__ == '__main__':
    unittest.main()
