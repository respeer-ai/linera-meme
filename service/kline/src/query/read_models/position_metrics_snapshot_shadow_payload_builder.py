class PositionMetricsSnapshotShadowPayloadBuilder:
    def build(
        self,
        *,
        position: dict,
        projected_metrics: dict,
        fee_calculation_complete: bool,
        principal_calculation_complete: bool,
        snapshot_shadow: dict,
    ) -> dict:
        return {
            'owner': position['owner'],
            'pool_application': position['pool_application'],
            'pool_id': position['pool_id'],
            'status': position.get('status') or 'active',
            'metrics_status': projected_metrics.get('metrics_status'),
            'fee_calculation_complete': fee_calculation_complete,
            'principal_calculation_complete': principal_calculation_complete,
            'snapshot_shadow': snapshot_shadow,
        }
