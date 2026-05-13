class TimeCodec:
    def event_time_ms_from_transaction(self, transaction: dict[str, object]) -> int | None:
        micros = transaction.get('created_at_micros')
        if micros not in (None, ''):
            return int(micros) // 1000
        created_at = transaction.get('created_at')
        if created_at in (None, ''):
            return None
        return int(created_at)

    def row_time_ms(self, row: dict[str, object], *keys: str) -> int | None:
        for key in keys:
            value = row.get(key)
            if value not in (None, ''):
                return int(value)
        return None
