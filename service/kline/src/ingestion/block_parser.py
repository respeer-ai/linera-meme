import json


class LayerOneBlockParser:
    """Normalizes fetched chain blocks into the local Layer 1 raw-ingest shape."""

    def parse(self, chain_id: str, height: int, payload: dict) -> dict:
        if payload.get('block'):
            payload = self._normalize_confirmed_block(payload)

        block_hash = payload.get('block_hash') or payload.get('hash')
        if not block_hash:
            raise ValueError(f'Missing block hash for {chain_id}@{height}')

        normalized = {
            'chain_id': chain_id,
            'height': int(payload.get('height', height)),
            'block_hash': str(block_hash),
            'timestamp_ms': int(payload.get('timestamp_ms', 0)),
            'epoch': payload.get('epoch'),
            'state_hash': payload.get('state_hash'),
            'previous_block_hash': payload.get('previous_block_hash'),
            'authenticated_owner': payload.get('authenticated_owner'),
            'operation_count': int(payload.get('operation_count', len(payload.get('operations', [])))),
            'incoming_bundle_count': int(payload.get('incoming_bundle_count', len(payload.get('incoming_bundles', [])))),
            'message_count': int(payload.get('message_count', len(payload.get('outgoing_messages', [])))),
            'event_count': int(payload.get('event_count', len(payload.get('events', [])))),
            'blob_count': int(payload.get('blob_count', 0)),
            'raw_block_bytes': payload.get('raw_block_bytes', str(payload).encode()),
            'incoming_bundles': self._normalize_incoming_bundles(payload.get('incoming_bundles', [])),
            'operations': self._normalize_operations(payload.get('operations', [])),
            'outgoing_messages': self._normalize_outgoing_messages(payload.get('outgoing_messages', [])),
            'events': self._normalize_events(payload.get('events', [])),
            'oracle_responses': self._normalize_oracle_responses(payload.get('oracle_responses', [])),
        }
        return normalized

    def _normalize_confirmed_block(self, payload: dict) -> dict:
        block = payload.get('block') or {}
        header = block.get('header') or {}
        body = block.get('body') or {}
        transaction_metadata = list(body.get('transactionMetadata') or [])

        incoming_bundles = []
        operations = []
        for transaction_index, metadata in enumerate(transaction_metadata):
            incoming_bundle = metadata.get('incomingBundle')
            if incoming_bundle is not None:
                incoming_bundles.append(
                    self._build_incoming_bundle(transaction_index, incoming_bundle)
                )
            operation = metadata.get('operation')
            if operation is not None:
                operations.append(self._build_operation(transaction_index, operation))

        outgoing_messages = self._build_outgoing_messages(body.get('messages') or [])
        events = self._build_events(body.get('events') or [])
        oracle_responses = self._build_oracle_responses(body.get('oracleResponses') or [])
        blobs = body.get('blobs') or []

        return {
            'block_hash': payload.get('hash'),
            'height': int(header.get('height', 0)),
            'timestamp_ms': self._normalize_timestamp_ms(header.get('timestamp')),
            'epoch': header.get('epoch'),
            'state_hash': header.get('stateHash'),
            'previous_block_hash': header.get('previousBlockHash'),
            'authenticated_owner': header.get('authenticatedSigner'),
            'operation_count': len(operations),
            'incoming_bundle_count': len(incoming_bundles),
            'message_count': len(outgoing_messages),
            'event_count': len(events),
            'blob_count': sum(len(batch or []) for batch in blobs),
            'raw_block_bytes': self._encode_raw_bytes(payload),
            'incoming_bundles': incoming_bundles,
            'operations': operations,
            'outgoing_messages': outgoing_messages,
            'events': events,
            'oracle_responses': oracle_responses,
        }

    def _build_incoming_bundle(self, transaction_index: int, bundle: dict) -> dict:
        message_bundle = bundle.get('bundle') or {}
        return {
            'bundle_index': transaction_index,
            'origin_chain_id': self._normalize_origin_chain_id(bundle.get('origin')),
            'action': str(bundle.get('action', 'Accept')),
            'source_height': int(message_bundle.get('height', 0)),
            'source_timestamp_ms': self._normalize_timestamp_ms(message_bundle.get('timestamp')),
            'source_cert_hash': str(message_bundle.get('certificateHash', '')),
            'transaction_index': int(message_bundle.get('transactionIndex', transaction_index)),
            'posted_messages': self._build_posted_messages(
                messages=message_bundle.get('messages') or [],
                transaction_index=int(message_bundle.get('transactionIndex', transaction_index)),
            ),
        }

    def _build_posted_messages(self, messages: list[dict], transaction_index: int) -> list[dict]:
        normalized = []
        for message_index, message in enumerate(messages):
            message_metadata = message.get('messageMetadata') or {}
            system_message = message_metadata.get('systemMessage') or {}
            normalized.append({
                'message_index': int(message.get('index', message_index)),
                'origin_chain_id': None,
                'source_cert_hash': None,
                'transaction_index': transaction_index,
                'authenticated_owner': message.get('authenticatedSigner'),
                'grant_amount': self._string_or_none(message.get('grant')),
                'refund_grant_to': message.get('refundGrantTo'),
                'message_kind': str(message.get('kind', 'Simple')),
                'message_type': str(message_metadata.get('messageType', 'User')),
                'application_id': message_metadata.get('applicationId'),
                'system_message_type': system_message.get('systemMessageType'),
                'system_target': ((system_message.get('credit') or {}).get('target')),
                'system_amount': self._string_or_none(
                    ((system_message.get('credit') or {}).get('amount'))
                    or ((system_message.get('withdraw') or {}).get('amount'))
                ),
                'system_source': ((system_message.get('credit') or {}).get('source')),
                'system_owner': ((system_message.get('withdraw') or {}).get('owner')),
                'system_recipient': ((system_message.get('withdraw') or {}).get('recipient')),
                'raw_message_bytes': self._message_bytes_from_graphql(
                    message_metadata.get('userBytesHex'),
                    message.get('message'),
                ),
            })
        return normalized

    def _build_operation(self, transaction_index: int, operation: dict) -> dict:
        system_operation = operation.get('systemOperation') or {}
        return {
            'operation_index': transaction_index,
            'operation_type': str(operation.get('operationType', 'User')),
            'application_id': operation.get('applicationId'),
            'system_operation_type': system_operation.get('systemOperationType'),
            'authenticated_owner': None,
            'raw_operation_bytes': self._operation_bytes_from_graphql(
                operation.get('userBytesHex'),
                system_operation,
            ),
        }

    def _build_outgoing_messages(self, transactions: list[list[dict]]) -> list[dict]:
        normalized = []
        for transaction_index, messages in enumerate(transactions):
            for message_index, message in enumerate(messages or []):
                metadata = self._outgoing_message_metadata(message.get('message'))
                system_message = metadata.get('systemMessage') or {}
                normalized.append({
                    'transaction_index': transaction_index,
                    'message_index': message_index,
                    'destination_chain_id': self._stringify_chain_target(
                        message.get('destination')
                    ),
                    'authenticated_owner': message.get('authenticatedSigner'),
                    'grant_amount': self._string_or_none(message.get('grant')),
                    'message_kind': str(message.get('kind', 'Simple')),
                    'message_type': str(metadata.get('messageType', 'User')),
                    'application_id': metadata.get('applicationId'),
                    'system_message_type': system_message.get('systemMessageType'),
                    'system_target': ((system_message.get('credit') or {}).get('target')),
                    'system_amount': self._string_or_none(
                        ((system_message.get('credit') or {}).get('amount'))
                        or ((system_message.get('withdraw') or {}).get('amount'))
                    ),
                    'system_source': ((system_message.get('credit') or {}).get('source')),
                    'system_owner': ((system_message.get('withdraw') or {}).get('owner')),
                    'system_recipient': ((system_message.get('withdraw') or {}).get('recipient')),
                    'raw_message_bytes': self._encode_raw_bytes(message.get('message')),
                })
        return normalized

    def _build_events(self, transactions: list[list[dict]]) -> list[dict]:
        normalized = []
        for transaction_index, events in enumerate(transactions):
            for event_index, event in enumerate(events or []):
                normalized.append({
                    'transaction_index': transaction_index,
                    'event_index': event_index,
                    'stream_id': self._stream_id(event.get('streamId')),
                    'stream_index': int(event.get('index', 0)),
                    'raw_event_bytes': self._encode_raw_bytes(event.get('value')),
                })
        return normalized

    def _build_oracle_responses(self, transactions: list[list]) -> list[dict]:
        normalized = []
        for transaction_index, responses in enumerate(transactions):
            for response_index, response in enumerate(responses or []):
                normalized.append({
                    'transaction_index': transaction_index,
                    'response_index': response_index,
                    'response_type': self._oracle_response_type(response),
                    'blob_hash': self._oracle_blob_hash(response),
                    'raw_response_bytes': self._encode_raw_bytes(response),
                })
        return normalized

    def _normalize_timestamp_ms(self, value) -> int:
        if value is None:
            return 0
        timestamp = int(value)
        if timestamp >= 1_000_000_000_000_000:
            return timestamp // 1000
        return timestamp

    def _normalize_origin_chain_id(self, origin) -> str:
        if isinstance(origin, dict):
            if origin.get('sender'):
                return str(origin['sender'])
            return self._encode_raw_text(origin)
        if origin is None:
            return ''
        return str(origin)

    def _message_bytes_from_graphql(self, user_bytes_hex, fallback_payload) -> bytes:
        if user_bytes_hex:
            return self._decode_hex_bytes(user_bytes_hex)
        return self._encode_raw_bytes(fallback_payload)

    def _operation_bytes_from_graphql(self, user_bytes_hex, fallback_payload) -> bytes:
        if user_bytes_hex:
            return self._decode_hex_bytes(user_bytes_hex)
        return self._encode_raw_bytes(fallback_payload)

    def _decode_hex_bytes(self, value: str) -> bytes:
        normalized = value[2:] if value.startswith('0x') else value
        return bytes.fromhex(normalized)

    def _encode_raw_bytes(self, payload) -> bytes:
        if isinstance(payload, bytes):
            return payload
        return self._encode_raw_text(payload)

    def _encode_raw_text(self, payload) -> bytes:
        if isinstance(payload, (dict, list, tuple, bool, int, float)) or payload is None:
            return json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(',', ':'),
            ).encode()
        return str(payload).encode()

    def _outgoing_message_metadata(self, message_payload) -> dict:
        if isinstance(message_payload, dict):
            if 'User' in message_payload:
                user_message = message_payload['User'] or {}
                return {
                    'messageType': 'User',
                    'applicationId': user_message.get('application_id'),
                    'userBytesHex': user_message.get('bytes'),
                }
            if 'System' in message_payload:
                system_payload = message_payload['System'] or {}
                system_message_type = next(iter(system_payload.keys()), None)
                metadata = {
                    'messageType': 'System',
                    'systemMessage': {
                        'systemMessageType': system_message_type,
                    },
                }
                if system_payload.get('Credit'):
                    metadata['systemMessage']['credit'] = system_payload['Credit']
                if system_payload.get('Withdraw'):
                    metadata['systemMessage']['withdraw'] = system_payload['Withdraw']
                return metadata
        return {}

    def _stream_id(self, stream_id) -> str:
        if isinstance(stream_id, dict):
            application_id = stream_id.get('applicationId') or ''
            stream_name = stream_id.get('streamName') or ''
            return f'{application_id}:{stream_name}'
        if stream_id is None:
            return ''
        return str(stream_id)

    def _oracle_response_type(self, response) -> str:
        if isinstance(response, dict) and len(response) == 1:
            return str(next(iter(response.keys())))
        return type(response).__name__

    def _oracle_blob_hash(self, response) -> str | None:
        if isinstance(response, dict):
            blob = response.get('blobHash')
            if blob is not None:
                return str(blob)
            if len(response) == 1 and isinstance(next(iter(response.values())), dict):
                nested = next(iter(response.values()))
                blob = nested.get('blobHash')
                if blob is not None:
                    return str(blob)
        return None

    def _string_or_none(self, value) -> str | None:
        if value is None:
            return None
        return str(value)

    def _stringify_chain_target(self, value) -> str:
        if value is None:
            return ''
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))

    def _normalize_incoming_bundles(self, bundles: list[dict]) -> list[dict]:
        normalized = []
        for bundle_index, bundle in enumerate(bundles):
            normalized.append({
                'bundle_index': int(bundle.get('bundle_index', bundle_index)),
                'origin_chain_id': str(bundle['origin_chain_id']),
                'action': str(bundle.get('action', 'Accept')),
                'source_height': int(bundle.get('source_height', 0)),
                'source_timestamp_ms': int(bundle.get('source_timestamp_ms', 0)),
                'source_cert_hash': str(bundle.get('source_cert_hash', '')),
                'transaction_index': int(bundle.get('transaction_index', 0)),
                'posted_messages': self._normalize_posted_messages(bundle.get('posted_messages', [])),
            })
        return normalized

    def _normalize_posted_messages(self, messages: list[dict]) -> list[dict]:
        normalized = []
        for message_index, message in enumerate(messages):
            normalized.append({
                'message_index': int(message.get('message_index', message_index)),
                'origin_chain_id': message.get('origin_chain_id'),
                'source_cert_hash': message.get('source_cert_hash'),
                'transaction_index': int(message.get('transaction_index', 0)),
                'authenticated_owner': message.get('authenticated_owner'),
                'grant_amount': message.get('grant_amount'),
                'refund_grant_to': message.get('refund_grant_to'),
                'message_kind': str(message.get('message_kind', 'Simple')),
                'message_type': str(message.get('message_type', 'User')),
                'application_id': message.get('application_id'),
                'system_message_type': message.get('system_message_type'),
                'system_target': message.get('system_target'),
                'system_amount': message.get('system_amount'),
                'system_source': message.get('system_source'),
                'system_owner': message.get('system_owner'),
                'system_recipient': message.get('system_recipient'),
                'raw_message_bytes': message.get('raw_message_bytes', b''),
            })
        return normalized

    def _normalize_operations(self, operations: list[dict]) -> list[dict]:
        normalized = []
        for operation_index, operation in enumerate(operations):
            normalized.append({
                'operation_index': int(operation.get('operation_index', operation_index)),
                'operation_type': str(operation.get('operation_type', 'User')),
                'application_id': operation.get('application_id'),
                'system_operation_type': operation.get('system_operation_type'),
                'authenticated_owner': operation.get('authenticated_owner'),
                'raw_operation_bytes': operation.get('raw_operation_bytes', b''),
            })
        return normalized

    def _normalize_outgoing_messages(self, messages: list[dict]) -> list[dict]:
        normalized = []
        for message_index, message in enumerate(messages):
            normalized.append({
                'transaction_index': int(message.get('transaction_index', 0)),
                'message_index': int(message.get('message_index', message_index)),
                'destination_chain_id': str(message.get('destination_chain_id', '')),
                'authenticated_owner': message.get('authenticated_owner'),
                'grant_amount': message.get('grant_amount'),
                'message_kind': str(message.get('message_kind', 'Simple')),
                'message_type': str(message.get('message_type', 'User')),
                'application_id': message.get('application_id'),
                'system_message_type': message.get('system_message_type'),
                'system_target': message.get('system_target'),
                'system_amount': message.get('system_amount'),
                'system_source': message.get('system_source'),
                'system_owner': message.get('system_owner'),
                'system_recipient': message.get('system_recipient'),
                'raw_message_bytes': message.get('raw_message_bytes', b''),
            })
        return normalized

    def _normalize_events(self, events: list[dict]) -> list[dict]:
        normalized = []
        for event_index, event in enumerate(events):
            normalized.append({
                'transaction_index': int(event.get('transaction_index', 0)),
                'event_index': int(event.get('event_index', event_index)),
                'stream_id': str(event.get('stream_id', '')),
                'stream_index': int(event.get('stream_index', 0)),
                'raw_event_bytes': event.get('raw_event_bytes', b''),
            })
        return normalized

    def _normalize_oracle_responses(self, responses: list[dict]) -> list[dict]:
        normalized = []
        for response_index, response in enumerate(responses):
            normalized.append({
                'transaction_index': int(response.get('transaction_index', 0)),
                'response_index': int(response.get('response_index', response_index)),
                'response_type': str(response.get('response_type', 'unknown')),
                'blob_hash': response.get('blob_hash'),
                'raw_response_bytes': response.get('raw_response_bytes'),
            })
        return normalized
