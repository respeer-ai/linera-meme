from registry.decode_dispatch_result import DecodeDispatchResult
from registry.decoded_transaction_payload_normalizer import DecodedTransactionPayloadNormalizer


class DecodeScheduler:
    def __init__(self, decoder_dispatcher, runner=None):
        self.decoder_dispatcher = decoder_dispatcher
        self._runner = runner
        self._payload_normalizer = DecodedTransactionPayloadNormalizer()

    def decode_item(self, item: dict, *, reprocess_reason: str | None = None) -> dict[str, object]:
        self._validate_item(item)
        result = self.decoder_dispatcher.dispatch(
            application_id=item['application_id'],
            payload_kind=item['payload_kind'],
            raw_bytes=item['raw_bytes'],
        )
        return {
            'raw_fact_id': item['raw_fact_id'],
            'raw_table': item['raw_table'],
            'application_id': item['application_id'],
            'payload_kind': item['payload_kind'],
            'reprocess_reason': reprocess_reason,
            'decode_result': result.to_dict(),
        }

    def decode_batch(self, items: list[dict], *, reprocess_reason: str | None = None) -> list[dict[str, object]]:
        if not self._runner:
            return [
                self.decode_item(item, reprocess_reason=reprocess_reason)
                for item in items
            ]

        for item in items:
            self._validate_item(item)

        # Pre-resolve application types for all items
        app_registry = self.decoder_dispatcher.application_registry
        resolved = []
        for item in items:
            app = app_registry.resolve(item['application_id'])
            resolved.append({**item, '_app': app})

        # Collect items with resolved apps for batch Rust decode
        batch_requests = []
        batch_indices = []
        for i, r in enumerate(resolved):
            if r['_app'] is not None:
                batch_requests.append({
                    'app_type': r['_app']['app_type'],
                    'payload_kind': r['payload_kind'],
                    'application_id': r['application_id'],
                    'raw_bytes': r['raw_bytes'],
                })
                batch_indices.append(i)

        # Execute a single subprocess call for the entire batch
        batch_raw = []
        if batch_requests:
            batch_raw = self._runner.decode_batch(batch_requests)

        # Assemble results
        outputs = []
        result_idx = 0
        for i, r in enumerate(resolved):
            if r['_app'] is None:
                item_result = DecodeDispatchResult(
                    status=DecodeDispatchResult.STATUS_UNRESOLVED_APPLICATION,
                    application_id=r['application_id'],
                    payload_kind=r['payload_kind'],
                    decode_error='application_id is not registered',
                )
            else:
                raw = batch_raw[result_idx]
                result_idx += 1
                item_result = self._build_from_rust_result(r, raw)

            outputs.append({
                'raw_fact_id': r['raw_fact_id'],
                'raw_table': r['raw_table'],
                'application_id': r['application_id'],
                'payload_kind': r['payload_kind'],
                'reprocess_reason': reprocess_reason,
                'decode_result': item_result.to_dict(),
            })

        return outputs

    def _build_from_rust_result(self, item: dict, raw: dict) -> DecodeDispatchResult:
        app = item['_app']
        app_type = app['app_type']
        metadata_json = app.get('metadata_json')

        if raw.get('status') == 'ok':
            decoded_payload = raw.get('decoded_payload_json')
            # Pool messages need transaction_type canonicalization
            if app_type == 'pool' and item['payload_kind'] == 'message' and isinstance(decoded_payload, dict):
                decoded_payload = self._payload_normalizer.normalize(decoded_payload)
            return DecodeDispatchResult(
                status=DecodeDispatchResult.STATUS_DECODED,
                application_id=item['application_id'],
                payload_kind=item['payload_kind'],
                app_type=app_type,
                payload_type=raw.get('payload_type'),
                decoded_payload_json=decoded_payload,
                metadata_json=metadata_json,
                decoder_version=raw.get('decoder_version'),
            )

        return DecodeDispatchResult(
            status=DecodeDispatchResult.STATUS_DECODE_FAILED,
            application_id=item['application_id'],
            payload_kind=item['payload_kind'],
            app_type=app_type,
            decode_error=raw.get('error', 'rust decoder error'),
            metadata_json=metadata_json,
        )

    def _validate_item(self, item: dict) -> None:
        required_keys = {
            'raw_fact_id',
            'raw_table',
            'application_id',
            'payload_kind',
            'raw_bytes',
        }
        missing_keys = sorted(required_keys - set(item.keys()))
        if missing_keys:
            raise ValueError(f'missing decode item keys: {",".join(missing_keys)}')
        if not str(item['raw_fact_id']).strip():
            raise ValueError('raw_fact_id must be non-empty')
        if not str(item['raw_table']).strip():
            raise ValueError('raw_table must be non-empty')
        if not str(item['application_id']).strip():
            raise ValueError('application_id must be non-empty')
        if item['payload_kind'] not in {'operation', 'message', 'event'}:
            raise ValueError(f"unsupported payload_kind: {item['payload_kind']}")
        if not isinstance(item['raw_bytes'], (bytes, bytearray)):
            raise ValueError('raw_bytes must be bytes-like')
