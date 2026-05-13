class PositionMetricsDiagnosticRecorder:
    def __init__(self, db):
        self.db = db

    def record_inexact_metric(self, metric: dict):
        self.db.record_diagnostic_event(
            source='position_metrics',
            event_type='inexact_position_metrics',
            severity='warning',
            owner=metric['owner'],
            pool_application=metric['pool_application'],
            pool_id=metric['pool_id'],
            status=metric['status'],
            details={
                'fetch_stage': metric.get('fetch_stage'),
                'fetch_reason_code': metric.get('fetch_reason_code'),
                'metrics_status': metric.get('metrics_status'),
                'fee_calculation_complete': bool(metric.get('fee_calculation_complete')),
                'principal_calculation_complete': bool(metric.get('principal_calculation_complete')),
                'computation_blockers': list(metric.get('computation_blockers') or []),
                'value_warning_codes': list(metric.get('value_warning_codes') or []),
            },
        )

    def record_snapshot_shadow(self, diagnostic: dict):
        shadow = diagnostic.get('snapshot_shadow') or {}
        self.db.record_diagnostic_event(
            source='position_metrics',
            event_type='snapshot_shadow_gap',
            severity='warning',
            owner=diagnostic['owner'],
            pool_application=diagnostic['pool_application'],
            pool_id=diagnostic['pool_id'],
            status=diagnostic['status'],
            details={
                'fetch_stage': diagnostic.get('fetch_stage'),
                'fetch_reason_code': diagnostic.get('fetch_reason_code'),
                'metrics_status': diagnostic.get('metrics_status'),
                'fee_calculation_complete': bool(diagnostic.get('fee_calculation_complete')),
                'principal_calculation_complete': bool(diagnostic.get('principal_calculation_complete')),
                'comparable': bool(shadow.get('comparable')),
                'position_basis_snapshot_present': bool(shadow.get('position_basis_snapshot_present')),
                'pool_state_snapshot_present': bool(shadow.get('pool_state_snapshot_present')),
                'mismatch_codes': list(shadow.get('mismatch_codes') or []),
                'readiness': shadow.get('readiness'),
                'readiness_reason_codes': list(shadow.get('readiness_reason_codes') or []),
                'exact_case': shadow.get('exact_case'),
                'projected_position_status': shadow.get('projected_position_status'),
                'projected_current_liquidity': shadow.get('projected_current_liquidity'),
                'projected_metrics_status': shadow.get('projected_metrics_status'),
                'computation_blockers': list(shadow.get('computation_blockers') or []),
                'value_warning_codes': list(shadow.get('value_warning_codes') or []),
                'latest_position_transaction_id': shadow.get('latest_position_transaction_id'),
                'latest_position_created_at': shadow.get('latest_position_created_at'),
                'latest_pool_transaction_id': shadow.get('latest_pool_transaction_id'),
                'latest_pool_trade_time_ms': shadow.get('latest_pool_trade_time_ms'),
                'latest_pool_liquidity_event_time_ms': shadow.get('latest_pool_liquidity_event_time_ms'),
                'position_basis_snapshot': shadow.get('position_basis_snapshot'),
                'pool_state_snapshot': shadow.get('pool_state_snapshot'),
            },
        )
