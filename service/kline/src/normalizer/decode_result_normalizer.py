from normalizer.application_event_family_resolver import ApplicationEventFamilyResolver
from normalizer.pool_executed_event_shape_validator import PoolExecutedEventShapeValidator
from normalizer.normalized_event_result import NormalizedEventResult


class DecodeResultNormalizer:
    def __init__(self):
        self.event_family_resolver = ApplicationEventFamilyResolver()
        self.pool_executed_event_shape_validator = PoolExecutedEventShapeValidator()

    def normalize_item(self, item: dict) -> dict[str, object]:
        self._validate_item(item)
        normalized_event = self._build_event(self._normalized_item(item))
        return {
            'raw_fact_id': item['raw_fact_id'],
            'raw_table': item['raw_table'],
            'application_id': item['application_id'],
            'payload_kind': item['payload_kind'],
            'reprocess_reason': item.get('reprocess_reason'),
            'normalized_events': [normalized_event.to_dict()],
        }

    def normalize_batch(self, items: list[dict]) -> list[dict[str, object]]:
        return [self.normalize_item(item) for item in items]

    def _build_event(self, item: dict) -> NormalizedEventResult:
        decode_result = item['decode_result']
        decode_status = decode_result['status']
        event_family = self._event_family(item)
        event_type = self._event_type(item)
        correlation_key = self._correlation_key(item, event_family)
        return NormalizedEventResult(
            normalized_event_id=f"{item['raw_fact_id']}:{event_family}:{event_type}",
            raw_fact_id=item['raw_fact_id'],
            raw_table=item['raw_table'],
            application_id=item['application_id'],
            payload_kind=item['payload_kind'],
            event_family=event_family,
            event_type=event_type,
            correlation_key=correlation_key,
            normalization_status=self._normalization_status(item),
            event_payload_json=self._event_payload(item),
            source_chain_id=self._source_chain_id(item),
            target_chain_id=self._target_chain_id(item),
            source_block_hash=item.get('source_block_hash'),
            target_block_hash=item.get('target_block_hash') or item.get('block_hash'),
            source_cert_hash=item.get('source_cert_hash') or item.get('certificate_hash'),
            transaction_index=item.get('transaction_index'),
            message_index=item.get('message_index'),
            app_type=decode_result.get('app_type'),
            payload_type=decode_result.get('payload_type'),
            decode_status=decode_status,
            reprocess_reason=item.get('reprocess_reason'),
        )

    def _normalized_item(self, item: dict) -> dict[str, object]:
        decode_result = item['decode_result']
        shape_error = self.pool_executed_event_shape_validator.validate(decode_result)
        if shape_error is None:
            return item
        normalized_item = dict(item)
        normalized_item['decode_result'] = self._decode_failed_shape_result(
            decode_result=decode_result,
            error_text=shape_error,
        )
        return normalized_item

    def _decode_failed_shape_result(
        self,
        *,
        decode_result: dict[str, object],
        error_text: str,
    ) -> dict[str, object]:
        return {
            'status': 'decode_failed',
            'application_id': decode_result.get('application_id'),
            'payload_kind': decode_result.get('payload_kind'),
            'app_type': decode_result.get('app_type'),
            'payload_type': decode_result.get('payload_type'),
            'decoded_payload_json': decode_result.get('decoded_payload_json'),
            'decode_error': error_text,
            'metadata_json': decode_result.get('metadata_json'),
            'decoder_version': decode_result.get('decoder_version'),
        }

    def _event_family(self, item: dict) -> str:
        return self.event_family_resolver.resolve(item)

    def _event_type(self, item: dict) -> str:
        decode_result = item['decode_result']
        if decode_result['status'] != 'decoded':
            return item['payload_kind']
        return str(decode_result.get('payload_type') or 'unknown_payload')

    def _correlation_key(self, item: dict, event_family: str) -> str:
        decode_result = item['decode_result']
        app_type = decode_result.get('app_type') or 'unknown_app'
        primary_chain_id = (
            self._source_chain_id(item)
            or self._target_chain_id(item)
            or 'unknown_chain'
        )
        source_cert_hash = item.get('source_cert_hash') or item.get('certificate_hash')
        transaction_index = item.get('transaction_index')
        if source_cert_hash is not None and transaction_index is not None:
            return (
                f'{app_type}:{primary_chain_id}:{source_cert_hash}:'
                f'{transaction_index}:{event_family}'
            )
        return f'{app_type}:{item["raw_table"]}:{item["raw_fact_id"]}:{event_family}'

    def _normalization_status(self, item: dict) -> str:
        if item['decode_result']['status'] != 'decoded':
            return NormalizedEventResult.STATUS_DECODE_FAILED
        if self._is_rejected(item):
            return NormalizedEventResult.STATUS_REJECTED
        return NormalizedEventResult.STATUS_OBSERVED

    def _event_payload(self, item: dict) -> dict[str, object]:
        decode_result = item['decode_result']
        payload = {
            'decode_status': decode_result['status'],
            'decoded_payload_json': decode_result.get('decoded_payload_json'),
            'decode_error': decode_result.get('decode_error'),
            'metadata_json': decode_result.get('metadata_json'),
            'rejected': self._is_rejected(item),
            'reject_reason': item.get('reject_reason'),
        }
        raw_context = {
            'chain_id': item.get('chain_id'),
            'source_chain_id': item.get('source_chain_id'),
            'target_chain_id': item.get('target_chain_id'),
            'block_hash': item.get('block_hash'),
            'source_block_hash': item.get('source_block_hash'),
            'target_block_hash': item.get('target_block_hash'),
            'source_cert_hash': item.get('source_cert_hash') or item.get('certificate_hash'),
            'transaction_index': item.get('transaction_index'),
            'target_transaction_index': item.get('target_transaction_index'),
            'message_index': item.get('message_index'),
        }
        payload['raw_context'] = {
            key: value
            for key, value in raw_context.items()
            if value is not None
        }
        return payload

    def _source_chain_id(self, item: dict) -> str | None:
        return item.get('source_chain_id') or item.get('origin_chain_id')

    def _target_chain_id(self, item: dict) -> str | None:
        return item.get('target_chain_id') or item.get('chain_id')

    def _is_rejected(self, item: dict) -> bool:
        if item.get('rejected') is True:
            return True
        status = item.get('execution_status')
        if isinstance(status, str) and status.lower() == 'rejected':
            return True
        return bool(item.get('reject_reason'))

    def _validate_item(self, item: dict) -> None:
        required_keys = {
            'raw_fact_id',
            'raw_table',
            'application_id',
            'payload_kind',
            'decode_result',
        }
        missing_keys = sorted(required_keys - set(item.keys()))
        if missing_keys:
            raise ValueError(f'missing normalize item keys: {",".join(missing_keys)}')
        if item['payload_kind'] not in {'operation', 'message', 'event'}:
            raise ValueError(f"unsupported payload_kind: {item['payload_kind']}")
        decode_result = item['decode_result']
        if not isinstance(decode_result, dict):
            raise ValueError('decode_result must be a dict')
        decode_status = decode_result.get('status')
        if decode_status not in {
            'decoded',
            'unresolved_application',
            'unimplemented_decoder',
            'decode_failed',
        }:
            raise ValueError(f'unsupported decode status: {decode_status}')
