from decimal import Decimal, InvalidOperation

from account_codec import AccountCodec
from market.claim_balance_deriver import ClaimBalanceDeriver


class ClaimBalanceCorrelationDeriver:
    CORRELATION_DIAGNOSTIC = 'claim_delta_requires_new_transaction_correlation'

    def __init__(
        self,
        *,
        pool_catalog_repository=None,
        normalized_event_repository=None,
    ):
        self.pool_catalog_repository = pool_catalog_repository
        self.normalized_event_repository = normalized_event_repository
        self.account_codec = AccountCodec()
        self.item_deriver = ClaimBalanceDeriver()

    def derive_batch(self, events: list[dict[str, object]]) -> dict[str, object]:
        if not events:
            return {
                'outputs_by_event_id': {},
                'batch_outputs': [],
                'resolved_event_ids': set(),
            }
        pool_tokens = self._pool_tokens_by_application()
        batch_events_by_id = {
            str(event['normalized_event_id']): event
            for event in events
            if event.get('normalized_event_id') is not None
        }
        originals = self._unique_events(
            self._correlatable_messages(events)
            + self._repository_messages_for_new_transactions(events)
        )
        new_transactions = self._unique_events(
            self._new_transactions(events)
            + self._repository_new_transactions_for_messages(events)
        )

        outputs_by_event_id: dict[str, list[dict[str, object]]] = {}
        batch_outputs: list[dict[str, object]] = []
        resolved_event_ids: set[str] = set()
        emitted_pair_ids: set[str] = set()
        for original in originals:
            original_id = str(original['normalized_event_id'])
            matches = [
                new_transaction
                for new_transaction in new_transactions
                if self._matches(original, new_transaction)
            ]
            if not matches:
                continue
            if len(matches) != 1:
                outputs = [
                    self.item_deriver._diagnostic(
                        original,
                        'ambiguous_new_transaction_correlation',
                        source=self._message_type(original),
                        confidence='partial',
                    )
                ]
            else:
                pair_id = f"{original_id}:{matches[0]['normalized_event_id']}"
                if pair_id in emitted_pair_ids:
                    continue
                emitted_pair_ids.add(pair_id)
                outputs = self._derive_correlated_outputs(
                    original=original,
                    new_transaction=matches[0],
                    pool_tokens=pool_tokens,
                )
            if not outputs:
                continue
            resolved_event_ids.add(original_id)
            if original_id in batch_events_by_id:
                outputs_by_event_id.setdefault(original_id, []).extend(outputs)
            else:
                batch_outputs.extend(outputs)
        return {
            'outputs_by_event_id': outputs_by_event_id,
            'batch_outputs': batch_outputs,
            'resolved_event_ids': resolved_event_ids,
        }

    def filter_resolved_diagnostics(
        self,
        outputs: list[dict[str, object]],
        *,
        resolved_event_ids: set[str],
    ) -> list[dict[str, object]]:
        filtered = []
        for output in outputs:
            if (
                output.get('settled_output_type') == 'claim_balance_diagnostic'
                and output.get('diagnostic_type') == self.CORRELATION_DIAGNOSTIC
                and output.get('normalized_event_id') in resolved_event_ids
            ):
                continue
            filtered.append(output)
        return filtered

    def _derive_correlated_outputs(
        self,
        *,
        original: dict[str, object],
        new_transaction: dict[str, object],
        pool_tokens: dict[str, tuple[str, str]],
    ) -> list[dict[str, object]]:
        pool_application = self.item_deriver._pool_application(original)
        tokens = pool_tokens.get(pool_application)
        if tokens is None:
            return [
                self.item_deriver._diagnostic(
                    original,
                    'missing_pool_token_metadata',
                    source=self._message_type(original),
                    confidence='partial',
                )
            ]
        payload = self._decoded_payload(original)
        transaction = self._transaction(new_transaction)
        message_type = payload.get('message_type')
        if message_type == 'swap':
            return self._swap_outputs(original, payload, transaction, tokens)
        if message_type == 'add_liquidity':
            return self._add_liquidity_outputs(original, payload, transaction, tokens)
        if message_type == 'remove_liquidity':
            return self._remove_liquidity_outputs(original, payload, transaction, tokens)
        return []

    def _swap_outputs(self, original, payload, transaction, tokens):
        owner = self._recipient(payload)
        if owner is None:
            return []
        transaction_type = self._transaction_type(transaction)
        if transaction_type in {'BuyToken0', 'buy_token_0'}:
            amount = transaction.get('amount_0_out')
            token = self._slot_token(tokens, 0)
        elif transaction_type in {'SellToken0', 'sell_token_0'}:
            amount = transaction.get('amount_1_out')
            token = self._slot_token(tokens, 1)
        else:
            return []
        if not self._positive(amount):
            return []
        return [
            self._correlated_delta(
                original,
                'claimable',
                'credit',
                token,
                owner,
                amount,
                'correlated_swap_new_transaction',
            )
        ]

    def _add_liquidity_outputs(self, original, payload, transaction, tokens):
        owner = self.account_codec.public_account_from_payload(payload.get('origin'))
        if owner is None:
            return []
        deltas = []
        for slot in (0, 1):
            requested = payload.get(f'amount_{slot}_in')
            accepted = transaction.get(f'amount_{slot}_in')
            excess = self._subtract(requested, accepted)
            if excess is None or excess <= Decimal(0):
                continue
            deltas.append(
                self._correlated_delta(
                    original,
                    'claimable',
                    'credit',
                    self._slot_token(tokens, slot),
                    owner,
                    self._amount_string(excess),
                    'correlated_add_liquidity_new_transaction',
                )
            )
        return deltas

    def _remove_liquidity_outputs(self, original, payload, transaction, tokens):
        owner = self._recipient(payload)
        if owner is None:
            return []
        deltas = []
        for slot in (0, 1):
            amount = transaction.get(f'amount_{slot}_out')
            if not self._positive(amount):
                continue
            deltas.append(
                self._correlated_delta(
                    original,
                    'claimable',
                    'credit',
                    self._slot_token(tokens, slot),
                    owner,
                    amount,
                    'correlated_remove_liquidity_new_transaction',
                )
            )
        return deltas

    def _correlated_delta(self, event, balance_kind, direction, token, owner, amount, source):
        delta = self.item_deriver._delta(
            event,
            balance_kind,
            direction,
            token,
            owner,
            amount,
            source,
        )
        delta['claim_balance_delta_id'] = (
            f"{event['normalized_event_id']}:{source}:"
            f"{balance_kind}:{direction}:{token}:{owner}:{amount}"
        )
        delta['derivation_confidence'] = 'exact'
        return delta

    def _matches(self, original, new_transaction) -> bool:
        if str(original.get('application_id')) != str(new_transaction.get('application_id')):
            return False
        source_block = original.get('target_block_hash') or original.get('source_block_hash')
        if source_block in (None, ''):
            return False
        if str(new_transaction.get('source_cert_hash')) != str(source_block):
            return False
        if not self._origin_matches_transaction(original, new_transaction):
            return False
        message_type = self._message_type(original)
        transaction_type = self._transaction_type(self._transaction(new_transaction))
        if message_type == 'swap':
            return self._swap_matches_transaction(original, new_transaction, transaction_type)
        if message_type == 'add_liquidity':
            return (
                transaction_type in {'AddLiquidity', 'add_liquidity'}
                and self._accepted_amount_is_not_greater(original, new_transaction, 0)
                and self._accepted_amount_is_not_greater(original, new_transaction, 1)
            )
        if message_type == 'remove_liquidity':
            return (
                transaction_type in {'RemoveLiquidity', 'remove_liquidity'}
                and self._amounts_equal(
                    self._decoded_payload(original).get('liquidity'),
                    self._transaction(new_transaction).get('liquidity'),
                )
            )
        return False

    def _swap_matches_transaction(self, original, new_transaction, transaction_type):
        payload = self._decoded_payload(original)
        transaction = self._transaction(new_transaction)
        amount_0_in = payload.get('amount_0_in')
        amount_1_in = payload.get('amount_1_in')
        if amount_0_in is not None:
            return (
                transaction_type in {'SellToken0', 'sell_token_0'}
                and self._amounts_equal(amount_0_in, transaction.get('amount_0_in'))
            )
        if amount_1_in is not None:
            return (
                transaction_type in {'BuyToken0', 'buy_token_0'}
                and self._amounts_equal(amount_1_in, transaction.get('amount_1_in'))
            )
        return False

    def _origin_matches_transaction(self, original, new_transaction):
        origin = self.account_codec.public_account_from_payload(
            self._decoded_payload(original).get('origin')
        )
        from_account = self.account_codec.public_account_from_payload(
            self._transaction(new_transaction).get('from')
        )
        return origin is not None and origin == from_account

    def _accepted_amount_is_not_greater(self, original, new_transaction, slot):
        requested = self._decimal(self._decoded_payload(original).get(f'amount_{slot}_in'))
        accepted = self._decimal(self._transaction(new_transaction).get(f'amount_{slot}_in'))
        return requested is not None and accepted is not None and accepted <= requested

    def _amounts_equal(self, left, right):
        left_value = self._decimal(left)
        right_value = self._decimal(right)
        return left_value is not None and right_value is not None and left_value == right_value

    def _repository_messages_for_new_transactions(self, events):
        if self.normalized_event_repository is None:
            return []
        messages = []
        for event in self._new_transactions(events):
            source_cert_hash = event.get('source_cert_hash')
            if source_cert_hash in (None, ''):
                continue
            list_messages = getattr(
                self.normalized_event_repository,
                'list_correlatable_pool_messages',
                None,
            )
            if list_messages is None:
                continue
            messages.extend(
                list_messages(
                    application_id=str(event['application_id']),
                    target_block_hash=str(source_cert_hash),
                )
            )
        return messages

    def _repository_new_transactions_for_messages(self, events):
        if self.normalized_event_repository is None:
            return []
        new_transactions = []
        list_new_transactions = getattr(
            self.normalized_event_repository,
            'list_pool_new_transactions_for_source_block',
            None,
        )
        if list_new_transactions is None:
            return []
        for event in self._correlatable_messages(events):
            source_block = event.get('target_block_hash') or event.get('source_block_hash')
            if source_block in (None, ''):
                continue
            new_transactions.extend(
                list_new_transactions(
                    application_id=str(event['application_id']),
                    source_cert_hash=str(source_block),
                )
            )
        return new_transactions

    def _correlatable_messages(self, events):
        return [
            event
            for event in events
            if event.get('normalization_status') == 'observed'
            and self._message_type(event) in {'swap', 'add_liquidity', 'remove_liquidity'}
        ]

    def _new_transactions(self, events):
        return [
            event
            for event in events
            if event.get('normalization_status') == 'observed'
            and self._message_type(event) == 'new_transaction'
        ]

    def _unique_events(self, events):
        unique = {}
        for event in events:
            event_id = event.get('normalized_event_id')
            if event_id is None:
                continue
            unique[str(event_id)] = event
        return list(unique.values())

    def _pool_tokens_by_application(self):
        if self.pool_catalog_repository is None:
            return {}
        list_pools = getattr(self.pool_catalog_repository, 'list_current_pools', None)
        if list_pools is None:
            list_pools = getattr(self.pool_catalog_repository, 'list_pool_catalog', None)
        if list_pools is None:
            return {}
        pools = list_pools() or []
        return {
            str(pool['pool_application']): (
                str(pool['token_0']),
                str(pool['token_1']),
            )
            for pool in pools
            if pool.get('pool_application') not in (None, '')
            and pool.get('token_0') not in (None, '')
            and pool.get('token_1') not in (None, '')
        }

    def _recipient(self, payload):
        return (
            self.account_codec.public_account_from_payload(payload.get('to'))
            or self.account_codec.public_account_from_payload(payload.get('origin'))
        )

    def _slot_token(self, tokens, slot):
        token = tokens[slot]
        if slot == 1 and token == 'TLINERA':
            return 'native'
        return token

    def _message_type(self, event):
        return str(self._decoded_payload(event).get('message_type'))

    def _transaction_type(self, transaction):
        value = transaction.get('transaction_type')
        if value is None:
            return None
        return str(value)

    def _transaction(self, event):
        payload = self._decoded_payload(event)
        transaction = payload.get('transaction')
        return transaction if isinstance(transaction, dict) else {}

    def _decoded_payload(self, event):
        payload = event.get('event_payload_json')
        if not isinstance(payload, dict):
            return {}
        decoded_payload = payload.get('decoded_payload_json')
        if not isinstance(decoded_payload, dict):
            return {}
        return decoded_payload

    def _positive(self, amount):
        value = self._decimal(amount)
        return value is not None and value > Decimal(0)

    def _subtract(self, left, right):
        left_value = self._decimal(left)
        right_value = self._decimal(right)
        if left_value is None or right_value is None:
            return None
        return left_value - right_value

    def _decimal(self, value):
        if value in (None, ''):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def _amount_string(self, value):
        if value == value.to_integral_value():
            return str(int(value))
        return format(value.normalize(), 'f')
