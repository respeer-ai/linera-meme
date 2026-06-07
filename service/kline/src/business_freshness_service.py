class BusinessFreshnessService:
    def __init__(self, *, read_model, snapshot_store, on_snapshot_updated=None):
        self.read_model = read_model
        self.snapshot_store = snapshot_store
        self.on_snapshot_updated = on_snapshot_updated

    def check(
        self,
        *,
        chain_id: str | None = None,
        pool_application: str | None = None,
        trigger: str | None = None,
    ) -> dict:
        scope_key = self._scope_key(chain_id=chain_id, pool_application=pool_application)
        snapshot = self.read_model.load_snapshot(chain_id=chain_id, pool_application=pool_application)
        snapshot = dict(snapshot)
        snapshot['scope_key'] = scope_key
        snapshot['trigger'] = trigger
        stored_snapshot = self.snapshot_store.set_latest(scope_key, snapshot)
        if self.on_snapshot_updated is not None:
            self.on_snapshot_updated(stored_snapshot)
        return stored_snapshot

    def get_latest(
        self,
        *,
        chain_id: str | None = None,
        pool_application: str | None = None,
    ) -> dict | None:
        return self.snapshot_store.get_latest(
            self._scope_key(chain_id=chain_id, pool_application=pool_application)
        )

    def get_debug_payload(
        self,
        *,
        chain_id: str | None = None,
        pool_application: str | None = None,
    ) -> dict:
        latest = self.get_latest(chain_id=chain_id, pool_application=pool_application)
        computed = self.check(
            chain_id=chain_id,
            pool_application=pool_application,
            trigger='debug_request',
        )
        return {'computed': computed, 'latest': latest}

    def _scope_key(self, *, chain_id: str | None, pool_application: str | None) -> str:
        if pool_application is not None:
            return f'pool:{pool_application}'
        if chain_id is not None:
            return f'chain:{chain_id}'
        return 'global'
