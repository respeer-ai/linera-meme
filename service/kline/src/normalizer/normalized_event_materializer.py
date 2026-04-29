class NormalizedEventMaterializer:
    def __init__(self, decode_result_normalizer, normalized_event_repository):
        self.decode_result_normalizer = decode_result_normalizer
        self.normalized_event_repository = normalized_event_repository

    def materialize_item(self, item: dict) -> dict[str, object]:
        normalized = self.decode_result_normalizer.normalize_item(item)
        self.normalized_event_repository.upsert_normalized_events(
            normalized['normalized_events']
        )
        return normalized

    def materialize_batch(self, items: list[dict]) -> list[dict[str, object]]:
        normalized_batch = self.decode_result_normalizer.normalize_batch(items)
        events = []
        for normalized in normalized_batch:
            events.extend(normalized['normalized_events'])
        self.normalized_event_repository.upsert_normalized_events(events)
        return normalized_batch

