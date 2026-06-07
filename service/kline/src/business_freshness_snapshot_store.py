class BusinessFreshnessSnapshotStore:
    def __init__(self):
        self._snapshots = {}

    def set_latest(self, scope_key: str, snapshot: dict) -> dict:
        stored_snapshot = dict(snapshot)
        self._snapshots[scope_key] = stored_snapshot
        return dict(stored_snapshot)

    def get_latest(self, scope_key: str) -> dict | None:
        snapshot = self._snapshots.get(scope_key)
        if snapshot is None:
            return None
        return dict(snapshot)

    def list_latest(self) -> dict:
        return {
            scope_key: dict(snapshot)
            for scope_key, snapshot in self._snapshots.items()
        }
