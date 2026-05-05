from storage.mysql.position_metrics_snapshot_semantic_facts_projector import (
    PositionMetricsSnapshotSemanticFactsProjector,
)


class PositionStateProjectionRepository:
    def __init__(
        self,
        db,
        *,
        snapshot_semantic_facts_projector=None,
    ):
        self.db = db
        self.position_state_table = 'position_state_v2'
        self.snapshot_semantic_facts_projector = (
            snapshot_semantic_facts_projector
            or PositionMetricsSnapshotSemanticFactsProjector()
        )

    def get_position_basis_snapshot(
        self,
        *,
        owner: str,
        pool_application_id: str,
        status: str = 'active',
    ) -> dict | None:
        self.db.ensure_fresh_read_connection()
        cursor = self.db.cursor_dict
        try:
            cursor.execute(
                f'''
                SELECT *
                FROM {self.position_state_table}
                WHERE owner = %s
                  AND pool_application_id = %s
                  AND status = %s
                LIMIT 1
                ''',
                (owner, pool_application_id, status),
            )
            return self.snapshot_semantic_facts_projector.project(cursor.fetchone())
        except Exception:
            return None
