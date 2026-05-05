class PositionMetricsSnapshotShadowPayloadBuilder:
    def build(
        self,
        *,
        position: dict,
        live_metrics: dict,
        exact_fee_supported: bool,
        exact_principal_supported: bool,
        snapshot_shadow: dict,
    ) -> dict:
        return {
            'owner': position['owner'],
            'pool_application': position['pool_application'],
            'pool_id': position['pool_id'],
            'status': position.get('status') or 'active',
            'metrics_status': live_metrics.get('metrics_status'),
            'exact_fee_supported': exact_fee_supported,
            'exact_principal_supported': exact_principal_supported,
            'snapshot_shadow': snapshot_shadow,
        }
