class DecodeScheduler:
    def __init__(self, decoder_dispatcher):
        self.decoder_dispatcher = decoder_dispatcher

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
        return [
            self.decode_item(item, reprocess_reason=reprocess_reason)
            for item in items
        ]

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
