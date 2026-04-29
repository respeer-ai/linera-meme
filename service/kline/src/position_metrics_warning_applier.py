class PositionMetricsWarningApplier:
    def apply(
        self,
        metrics: dict,
        *,
        pool_history_gap_summary: dict | None = None,
    ) -> dict:
        warning_codes = list(metrics.get('value_warning_codes') or [])
        warning_message = metrics.get('value_warning_message')
        blockers = list(metrics.get('computation_blockers') or [])

        if (
            pool_history_gap_summary
            and bool(pool_history_gap_summary.get('has_internal_gaps'))
            and pool_history_gap_summary.get('basis') in {'archive_reconciliation', 'live_db_mismatch'}
        ):
            if 'pool_history_has_internal_gaps' not in blockers:
                blockers.append('pool_history_has_internal_gaps')
            metrics['exact_fee_supported'] = False
            metrics['exact_principal_supported'] = False
            warning_message = 'Current values are estimated from incomplete history and may change as data continues to reconcile.'

        if not metrics.get('exact_fee_supported'):
            if 'estimated_values' not in warning_codes:
                warning_codes.append('estimated_values')
            if warning_message is None:
                warning_message = 'Current values are estimated and may change as data continues to reconcile.'

        metrics['computation_blockers'] = blockers
        metrics['value_warning_codes'] = warning_codes
        metrics['value_warning_message'] = warning_message
        metrics['fee_amount0'] = metrics.get('fee_amount0') or '0'
        metrics['fee_amount1'] = metrics.get('fee_amount1') or '0'
        metrics['protocol_fee_amount0'] = metrics.get('protocol_fee_amount0') or '0'
        metrics['protocol_fee_amount1'] = metrics.get('protocol_fee_amount1') or '0'
        return metrics
