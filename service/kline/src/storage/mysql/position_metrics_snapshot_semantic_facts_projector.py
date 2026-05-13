from query.read_models.position_metrics_snapshot_semantic_facts import PositionMetricsSnapshotSemanticFacts


class PositionMetricsSnapshotSemanticFactsProjector:
    def project(self, snapshot: dict | None) -> dict | None:
        if snapshot is None:
            return None
        projected = dict(snapshot)
        projected['semantic_facts'] = PositionMetricsSnapshotSemanticFacts.from_state_payload(
            projected.get('state_payload_json')
        ).raw()
        return projected
