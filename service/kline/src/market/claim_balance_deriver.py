from account_codec import AccountCodec


class ClaimBalanceDeriver:
    def __init__(self):
        self.account_codec = AccountCodec()

    def derive_item(self, event: dict[str, object]) -> dict[str, object]:
        payload = self._decoded_payload(event)
        if payload is None:
            return self._result(event, outputs=[])

        message_type = payload.get('message_type')
        if event.get('normalization_status') == 'rejected':
            return self._rejected_message(event, message_type)
        if event.get('normalization_status') != 'observed':
            return self._result(event, outputs=[])

        if message_type == 'claim':
            return self._claim(event, payload)
        if message_type == 'claim_transfer_receipt':
            return self._claim_transfer_receipt(event, payload)
        if message_type == 'fund_result':
            return self._fund_result(event, payload)
        if message_type == 'add_liquidity_transfer_receipt':
            return self._add_liquidity_transfer_receipt(event, payload)
        if message_type == 'swap_transfer_receipt':
            return self._swap_transfer_receipt(event, payload)
        if message_type in {'swap', 'add_liquidity', 'remove_liquidity'}:
            return self._correlation_required_message(event, message_type)
        return self._result(event, outputs=[])

    def derive_batch(self, events: list[dict[str, object]]) -> list[dict[str, object]]:
        return [self.derive_item(event) for event in events]

    def _claim(self, event, payload):
        owner = self.account_codec.public_account_from_payload(payload.get('origin'))
        amount = payload.get('amount')
        token = self._token(payload.get('token'))
        if owner is None or amount is None:
            return self._result(event, outputs=[])

        outputs = [self._delta(event, 'claimable', 'debit', token, owner, amount, 'claim')]
        if payload.get('token') is not None:
            outputs.append(self._delta(event, 'claiming', 'credit', token, owner, amount, 'claim'))
        return self._result(event, outputs=outputs)

    def _claim_transfer_receipt(self, event, payload):
        receipt = payload.get('receipt')
        if not isinstance(receipt, dict):
            return self._result(event, outputs=[])
        owner = self.account_codec.public_account_from_payload(receipt.get('owner'))
        amount = receipt.get('amount')
        token = self._token(receipt.get('token'))
        if owner is None or amount is None:
            return self._result(event, outputs=[])

        outputs = [self._delta(event, 'claiming', 'debit', token, owner, amount, 'claim_transfer_receipt')]
        if self._is_err(receipt.get('result')):
            outputs.append(self._delta(event, 'claimable', 'credit', token, owner, amount, 'claim_transfer_receipt'))
        return self._result(event, outputs=outputs)

    def _fund_result(self, event, payload):
        request = payload.get('request')
        if not self._is_err(payload.get('result')):
            return self._result(event, outputs=[])
        if not isinstance(request, dict) or request.get('fund_type') != 'AddLiquidity':
            return self._result(event, outputs=[])
        return self._prev_credit(event, payload.get('prev'), 'fund_result')

    def _add_liquidity_transfer_receipt(self, event, payload):
        receipt = payload.get('receipt')
        if not isinstance(receipt, dict) or not self._is_err(receipt.get('result')):
            return self._result(event, outputs=[])
        return self._prev_credit(event, receipt.get('prev'), 'add_liquidity_transfer_receipt')

    def _swap_transfer_receipt(self, event, payload):
        receipt = payload.get('receipt')
        if not isinstance(receipt, dict) or not self._is_err(receipt.get('result')):
            return self._result(event, outputs=[])
        return self._result(event, outputs=[
            self._diagnostic(
                event,
                'swap_transfer_receipt_failure_has_no_claim_delta',
                source='swap_transfer_receipt',
            )
        ])

    def _rejected_message(self, event, message_type):
        if message_type not in {
            'swap',
            'add_liquidity',
            'remove_liquidity',
            'claim',
            'claim_transfer_receipt',
            'add_liquidity_transfer_receipt',
            'swap_transfer_receipt',
        }:
            return self._result(event, outputs=[])
        return self._result(event, outputs=[
            self._diagnostic(
                event,
                'rejected_message_no_handler_delta',
                source=str(message_type),
                confidence='exact',
                rejected=True,
            )
        ])

    def _correlation_required_message(self, event, message_type):
        return self._result(event, outputs=[
            self._diagnostic(
                event,
                'claim_delta_requires_new_transaction_correlation',
                source=str(message_type),
                confidence='partial',
            )
        ])

    def _prev_credit(self, event, prev, source):
        if not isinstance(prev, dict):
            return self._result(event, outputs=[])
        owner = self.account_codec.public_account_from_payload(prev.get('from'))
        amount = prev.get('amount_in')
        token = self._token(prev.get('token'))
        if owner is None or amount is None:
            return self._result(event, outputs=[])
        return self._result(event, outputs=[
            self._delta(event, 'claimable', 'credit', token, owner, amount, source)
        ])

    def _delta(self, event, balance_kind, direction, token, owner, amount, source):
        return {
            'settled_output_type': 'claim_balance_delta',
            'claim_balance_delta_id': f"{event['normalized_event_id']}:{source}:{balance_kind}:{direction}:{token}:{owner}",
            'normalized_event_id': event['normalized_event_id'],
            'pool_application_id': self._pool_application(event),
            'execution_chain_id': self._execution_chain_id(event),
            'token': token,
            'owner': owner,
            'balance_kind': balance_kind,
            'delta_amount': str(amount),
            'delta_direction': direction,
            'block_hash': event.get('target_block_hash') or event.get('source_block_hash'),
            'block_height': event.get('target_block_height') or event.get('source_block_height'),
            'transaction_index': event.get('transaction_index'),
            'message_index': event.get('message_index'),
            'rejected': False,
            'derivation_source': source,
            'derivation_confidence': 'exact',
            'source_event_key': event['normalized_event_id'],
            'event_payload_json': event.get('event_payload_json') or {},
        }

    def _diagnostic(
        self,
        event,
        diagnostic_type,
        *,
        source,
        confidence='exact',
        rejected=False,
    ):
        return {
            'settled_output_type': 'claim_balance_diagnostic',
            'claim_balance_diagnostic_id': f"{event['normalized_event_id']}:{diagnostic_type}:{source}",
            'normalized_event_id': event['normalized_event_id'],
            'pool_application_id': self._pool_application(event),
            'execution_chain_id': self._execution_chain_id(event),
            'diagnostic_type': diagnostic_type,
            'derivation_source': source,
            'derivation_confidence': confidence,
            'block_hash': event.get('target_block_hash') or event.get('source_block_hash'),
            'block_height': event.get('target_block_height') or event.get('source_block_height'),
            'transaction_index': event.get('transaction_index'),
            'message_index': event.get('message_index'),
            'rejected': rejected,
            'source_event_key': event['normalized_event_id'],
            'event_payload_json': event.get('event_payload_json') or {},
        }

    def _result(self, event, *, outputs):
        return {
            'normalized_event_id': event['normalized_event_id'],
            'source_event_key': event['normalized_event_id'],
            'derivation_status': 'settled' if outputs else 'ignored_non_settled',
            'settled_outputs': outputs,
            'error_text': None,
        }

    def _decoded_payload(self, event):
        payload = event.get('event_payload_json')
        if not isinstance(payload, dict):
            return None
        decoded_payload = payload.get('decoded_payload_json')
        if not isinstance(decoded_payload, dict):
            return None
        return decoded_payload

    def _pool_application(self, event):
        application_id = str(event['application_id'])
        if '@' in application_id:
            return application_id
        owner = application_id if application_id.startswith('0x') else f'0x{application_id}'
        return self.account_codec.format_account(chain_id=self._execution_chain_id(event), owner=owner)

    def _execution_chain_id(self, event):
        chain_id = event.get('target_chain_id') or event.get('source_chain_id')
        if chain_id in (None, ''):
            raise ValueError('missing_execution_chain_id')
        return str(chain_id)

    def _token(self, token):
        return 'native' if token is None else str(token)

    def _is_err(self, result):
        return isinstance(result, dict) and result.get('err') is not None
