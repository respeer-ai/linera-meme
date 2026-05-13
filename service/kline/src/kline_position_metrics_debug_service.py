from query.read_models.position_metrics import PositionMetricsReadModel


class KlinePositionMetricsDebugService:
    def __init__(
        self,
        *,
        runtime,
        position_metrics_public_api,
        position_metrics_dependencies_factory,
    ):
        self._runtime = runtime
        self._position_metrics_public_api = position_metrics_public_api
        self._position_metrics_dependencies_factory = position_metrics_dependencies_factory

    def _position_metrics_dependencies(self):
        return self._position_metrics_dependencies_factory()

    async def build_position_metrics_readiness_debug_payload(
        self,
        *,
        owner: str,
        status: str,
        sample_limit: int,
    ):
        dependencies = self._position_metrics_dependencies()
        read_model = PositionMetricsReadModel(
            dependencies.positions_repository(),
            dependencies.fetcher(
                position_metrics_public_api=self._position_metrics_public_api,
            ),
        )
        read_result = await read_model.get_position_metrics(
            owner=owner,
            status=status,
        )
        payload = read_result.public_payload()
        shadow_diagnostics = list(read_result.shadow_diagnostics)
        metric_diagnostics = list(read_result.metric_diagnostics)
        metric_by_key = {
            (
                row['owner'],
                row['pool_application'],
                int(row['pool_id']),
                row['status'],
            ): row
            for row in metric_diagnostics
        }
        shadow_by_key = {
            (
                row['owner'],
                row['pool_application'],
                int(row['pool_id']),
                row['status'],
            ): row
            for row in shadow_diagnostics
        }
        readiness_counts = {
            'candidate': 0,
            'snapshot_missing': 0,
            'structure_mismatch': 0,
            'financial_semantics_pending': 0,
            'shadow_unavailable': 0,
        }
        fetch_stage_counts = {}
        readiness_by_fetch_stage = {}
        fetch_reason_code_counts = {}
        fetch_reason_code_by_stage = {}
        exact_case_counts = {}
        readiness_reason_counts = {}
        mismatch_code_counts = {}
        basis_profile_counts = {}
        current_round_liquidity_event_count_counts = {}
        current_round_trade_count_before_basis_counts = {}
        trade_count_between_basis_and_fee_free_basis_counts = {}
        exact_current_principal_case_counts = {}
        materialized_protocol_fee_split_case_counts = {}
        protocol_fee_split_semantic_counts = {}
        protocol_fee_split_timing_case_counts = {}
        unresolved_protocol_fee_timing_case_counts = {}
        unresolved_protocol_fee_profile_counts = {}
        unresolved_protocol_fee_semantic_counts = {}
        unresolved_protocol_fee_boundary_status_counts = {}
        unresolved_protocol_fee_explanation_counts = {}
        fee_to_continuity_case_counts = {}
        protocol_fee_current_owner_provenance_case_counts = {}
        protocol_fee_current_owner_timing_case_counts = {}
        safe_fee_to_restored_counts = {
            'restored': 0,
            'not_restored': 0,
        }
        samples = []
        for metric in payload.get('metrics') or []:
            key = (
                metric['owner'],
                metric['pool_application'],
                int(metric['pool_id']),
                metric['status'],
            )
            shadow_row = shadow_by_key.get(key)
            metric_row = metric_by_key.get(key) or {}
            shadow = (shadow_row or {}).get('snapshot_shadow') or {}
            readiness = str(shadow.get('readiness') or 'shadow_unavailable')
            fetch_stage = str(
                (shadow_row or {}).get('fetch_stage')
                or metric_row.get('fetch_stage')
                or 'unknown'
            )
            fetch_reason_code = str(
                (shadow_row or {}).get('fetch_reason_code')
                or metric_row.get('fetch_reason_code')
                or 'unknown'
            )
            if readiness not in readiness_counts:
                readiness_counts[readiness] = 0
            readiness_counts[readiness] += 1
            fetch_stage_counts[fetch_stage] = fetch_stage_counts.get(fetch_stage, 0) + 1
            fetch_reason_code_counts[fetch_reason_code] = fetch_reason_code_counts.get(fetch_reason_code, 0) + 1
            if fetch_stage not in readiness_by_fetch_stage:
                readiness_by_fetch_stage[fetch_stage] = {}
            readiness_by_fetch_stage[fetch_stage][readiness] = (
                readiness_by_fetch_stage[fetch_stage].get(readiness, 0) + 1
            )
            if fetch_stage not in fetch_reason_code_by_stage:
                fetch_reason_code_by_stage[fetch_stage] = {}
            fetch_reason_code_by_stage[fetch_stage][fetch_reason_code] = (
                fetch_reason_code_by_stage[fetch_stage].get(fetch_reason_code, 0) + 1
            )
            exact_case = shadow.get('exact_case')
            if exact_case:
                exact_case = str(exact_case)
                exact_case_counts[exact_case] = exact_case_counts.get(exact_case, 0) + 1
            position_basis_snapshot = dict(shadow.get('position_basis_snapshot') or {})
            basis_type = position_basis_snapshot.get('basis_type')
            basis_opens_current_round = position_basis_snapshot.get('basis_opens_current_round')
            has_only_zero_liquidity_before_basis = position_basis_snapshot.get('has_only_zero_liquidity_before_basis')
            if basis_type is not None:
                basis_profile = '|'.join([
                    str(basis_type),
                    'current_round' if bool(basis_opens_current_round) else 'not_current_round',
                    'zero_bootstrap_only' if bool(has_only_zero_liquidity_before_basis) else 'non_zero_or_unknown_prefix',
                ])
                basis_profile_counts[basis_profile] = basis_profile_counts.get(basis_profile, 0) + 1
            else:
                basis_profile = None
            current_round_liquidity_event_count = position_basis_snapshot.get('current_round_liquidity_event_count')
            if current_round_liquidity_event_count not in (None, ''):
                current_round_liquidity_event_count = int(current_round_liquidity_event_count)
                count_key = str(current_round_liquidity_event_count)
                current_round_liquidity_event_count_counts[count_key] = (
                    current_round_liquidity_event_count_counts.get(count_key, 0) + 1
                )
            current_round_trade_count_before_basis = position_basis_snapshot.get('current_round_trade_count_before_basis')
            if current_round_trade_count_before_basis not in (None, ''):
                current_round_trade_count_before_basis = int(current_round_trade_count_before_basis)
                trade_count_key = str(current_round_trade_count_before_basis)
                current_round_trade_count_before_basis_counts[trade_count_key] = (
                    current_round_trade_count_before_basis_counts.get(trade_count_key, 0) + 1
                )
            trade_count_between_basis_and_fee_free_basis = position_basis_snapshot.get(
                'trade_count_between_basis_and_fee_free_basis'
            )
            if trade_count_between_basis_and_fee_free_basis not in (None, ''):
                trade_count_between_basis_and_fee_free_basis = int(trade_count_between_basis_and_fee_free_basis)
                trade_count_key = str(trade_count_between_basis_and_fee_free_basis)
                trade_count_between_basis_and_fee_free_basis_counts[trade_count_key] = (
                    trade_count_between_basis_and_fee_free_basis_counts.get(trade_count_key, 0) + 1
                )
            exact_current_principal_case = position_basis_snapshot.get('exact_current_principal_case')
            if exact_current_principal_case not in (None, ''):
                exact_current_principal_case = str(exact_current_principal_case)
                exact_current_principal_case_counts[exact_current_principal_case] = (
                    exact_current_principal_case_counts.get(exact_current_principal_case, 0) + 1
                )
            materialized_protocol_fee_split_case = position_basis_snapshot.get('materialized_protocol_fee_split_case')
            if materialized_protocol_fee_split_case not in (None, ''):
                materialized_protocol_fee_split_case = str(materialized_protocol_fee_split_case)
                materialized_protocol_fee_split_case_counts[materialized_protocol_fee_split_case] = (
                    materialized_protocol_fee_split_case_counts.get(materialized_protocol_fee_split_case, 0) + 1
                )
            protocol_fee_split_semantic = self._runtime.position_metrics_protocol_fee_split_semantics().semantic_for_case(
                materialized_protocol_fee_split_case
            )
            protocol_fee_split_semantic_counts[protocol_fee_split_semantic] = (
                protocol_fee_split_semantic_counts.get(protocol_fee_split_semantic, 0) + 1
            )
            fee_to_continuity_case = position_basis_snapshot.get('fee_to_continuity_case')
            if fee_to_continuity_case not in (None, ''):
                fee_to_continuity_case = str(fee_to_continuity_case)
                fee_to_continuity_case_counts[fee_to_continuity_case] = (
                    fee_to_continuity_case_counts.get(fee_to_continuity_case, 0) + 1
                )
            protocol_fee_current_owner_provenance_case = position_basis_snapshot.get(
                'protocol_fee_current_owner_provenance_case'
            )
            if protocol_fee_current_owner_provenance_case not in (None, ''):
                protocol_fee_current_owner_provenance_case = str(protocol_fee_current_owner_provenance_case)
                protocol_fee_current_owner_provenance_case_counts[protocol_fee_current_owner_provenance_case] = (
                    protocol_fee_current_owner_provenance_case_counts.get(
                        protocol_fee_current_owner_provenance_case,
                        0,
                    ) + 1
                )
            protocol_fee_current_owner_timing_case = self._protocol_fee_current_owner_timing_case(position_basis_snapshot)
            if protocol_fee_current_owner_timing_case not in (None, ''):
                protocol_fee_current_owner_timing_case_counts[protocol_fee_current_owner_timing_case] = (
                    protocol_fee_current_owner_timing_case_counts.get(
                        protocol_fee_current_owner_timing_case,
                        0,
                    ) + 1
                )
            if (
                materialized_protocol_fee_split_case not in (None, '')
                and protocol_fee_current_owner_timing_case not in (None, '')
            ):
                split_timing_key = (
                    f'{materialized_protocol_fee_split_case}|'
                    f'{protocol_fee_current_owner_timing_case}'
                )
                protocol_fee_split_timing_case_counts[split_timing_key] = (
                    protocol_fee_split_timing_case_counts.get(split_timing_key, 0) + 1
                )
                if materialized_protocol_fee_split_case == 'fee_to_nonzero_prior_add_basis_unresolved':
                    unresolved_protocol_fee_timing_case_counts[split_timing_key] = (
                        unresolved_protocol_fee_timing_case_counts.get(split_timing_key, 0) + 1
                    )
            unresolved_protocol_fee_profile = self._protocol_fee_unresolved_profile(
                materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
                protocol_fee_current_owner_timing_case=protocol_fee_current_owner_timing_case,
                fee_to_continuity_case=fee_to_continuity_case,
                protocol_fee_current_owner_provenance_case=protocol_fee_current_owner_provenance_case,
            )
            if unresolved_protocol_fee_profile not in (None, ''):
                unresolved_protocol_fee_profile_counts[unresolved_protocol_fee_profile] = (
                    unresolved_protocol_fee_profile_counts.get(unresolved_protocol_fee_profile, 0) + 1
                )
            unresolved_protocol_fee_semantic = self._runtime.position_metrics_protocol_fee_split_semantics().unresolved_semantic(
                unresolved_protocol_fee_profile
            )
            unresolved_protocol_fee_explanation = self._runtime.position_metrics_protocol_fee_split_semantics().unresolved_explanation(
                unresolved_protocol_fee_semantic
            )
            unresolved_protocol_fee_boundary_status = self._runtime.position_metrics_protocol_fee_split_semantics().unresolved_boundary_status(
                unresolved_protocol_fee_semantic
            )
            if unresolved_protocol_fee_profile not in (None, ''):
                unresolved_protocol_fee_semantic_counts[unresolved_protocol_fee_semantic] = (
                    unresolved_protocol_fee_semantic_counts.get(unresolved_protocol_fee_semantic, 0) + 1
                )
                unresolved_protocol_fee_boundary_status_counts[unresolved_protocol_fee_boundary_status] = (
                    unresolved_protocol_fee_boundary_status_counts.get(unresolved_protocol_fee_boundary_status, 0) + 1
                )
            if unresolved_protocol_fee_explanation not in (None, ''):
                unresolved_protocol_fee_explanation_counts[unresolved_protocol_fee_explanation] = (
                    unresolved_protocol_fee_explanation_counts.get(unresolved_protocol_fee_explanation, 0) + 1
                )
            safe_fee_to_restored = self._runtime.position_metrics_protocol_fee_split_semantics().is_safe_restored_case(
                materialized_protocol_fee_split_case
            )
            safe_fee_to_restored_counts['restored' if safe_fee_to_restored else 'not_restored'] += 1
            readiness_reason_codes = [str(code) for code in (shadow.get('readiness_reason_codes') or [])]
            mismatch_codes = [str(code) for code in (shadow.get('mismatch_codes') or [])]
            for code in readiness_reason_codes:
                readiness_reason_counts[code] = readiness_reason_counts.get(code, 0) + 1
            for code in mismatch_codes:
                mismatch_code_counts[code] = mismatch_code_counts.get(code, 0) + 1
            if len(samples) < sample_limit:
                samples.append({
                    'owner': metric['owner'],
                    'pool_application': metric['pool_application'],
                    'pool_id': metric['pool_id'],
                    'status': metric['status'],
                    'fetch_stage': fetch_stage,
                    'fetch_reason_code': fetch_reason_code,
                    'metrics_status': metric.get('metrics_status'),
                    'fee_calculation_complete': bool(metric.get('fee_calculation_complete')),
                    'principal_calculation_complete': bool(metric.get('principal_calculation_complete')),
                    'readiness': readiness,
                    'exact_case': exact_case,
                    'basis_profile': basis_profile,
                    'basis_type': basis_type,
                    'basis_opens_current_round': basis_opens_current_round,
                    'has_only_zero_liquidity_before_basis': has_only_zero_liquidity_before_basis,
                    'current_round_liquidity_event_count': current_round_liquidity_event_count,
                    'current_round_trade_count_before_basis': current_round_trade_count_before_basis,
                    'trade_count_between_basis_and_fee_free_basis': trade_count_between_basis_and_fee_free_basis,
                    'exact_current_principal_case': exact_current_principal_case,
                    'materialized_protocol_fee_split_case': materialized_protocol_fee_split_case,
                    'protocol_fee_split_semantic': protocol_fee_split_semantic,
                    'fee_to_continuity_case': fee_to_continuity_case,
                    'fee_to_continuity_change_count_after_basis': position_basis_snapshot.get(
                        'fee_to_continuity_change_count_after_basis'
                    ),
                    'fee_to_continuity_known_before_basis': position_basis_snapshot.get(
                        'fee_to_continuity_known_before_basis'
                    ),
                    'fee_to_account_at_basis': position_basis_snapshot.get('fee_to_account_at_basis'),
                    'fee_to_account_latest_known': position_basis_snapshot.get('fee_to_account_latest_known'),
                    'protocol_fee_current_owner_provenance_case': protocol_fee_current_owner_provenance_case,
                    'protocol_fee_current_owner_timing_case': protocol_fee_current_owner_timing_case,
                    'unresolved_protocol_fee_profile': unresolved_protocol_fee_profile,
                    'unresolved_protocol_fee_semantic': unresolved_protocol_fee_semantic,
                    'unresolved_protocol_fee_boundary_status': unresolved_protocol_fee_boundary_status,
                    'unresolved_protocol_fee_explanation': unresolved_protocol_fee_explanation,
                    'basis_protocol_fee_liquidity_owned_by_current_owner': position_basis_snapshot.get(
                        'basis_protocol_fee_liquidity_owned_by_current_owner'
                    ),
                    'post_basis_protocol_fee_liquidity_owned_by_current_owner': position_basis_snapshot.get(
                        'post_basis_protocol_fee_liquidity_owned_by_current_owner'
                    ),
                    'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': (
                        position_basis_snapshot.get('post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add')
                    ),
                    'protocol_fee_liquidity_owned_by_current_owner_current': position_basis_snapshot.get(
                        'protocol_fee_liquidity_owned_by_current_owner_current'
                    ),
                    'protocol_fee_liquidity_owned_by_other_accounts': position_basis_snapshot.get(
                        'protocol_fee_liquidity_owned_by_other_accounts'
                    ),
                    'protocol_fee_liquidity_owner_unknown': position_basis_snapshot.get(
                        'protocol_fee_liquidity_owner_unknown'
                    ),
                    'safe_fee_to_restored': safe_fee_to_restored,
                    'current_round_started_at': position_basis_snapshot.get('current_round_started_at'),
                    'current_round_started_transaction_id': position_basis_snapshot.get(
                        'current_round_started_transaction_id'
                    ),
                    'readiness_reason_codes': readiness_reason_codes,
                    'mismatch_codes': mismatch_codes,
                })
        return {
            'owner': owner,
            'status': status,
            'total_positions': len(payload.get('metrics') or []),
            'sample_limit': sample_limit,
            'readiness_counts': readiness_counts,
            'fetch_stage_counts': fetch_stage_counts,
            'readiness_by_fetch_stage': readiness_by_fetch_stage,
            'fetch_reason_code_counts': fetch_reason_code_counts,
            'fetch_reason_code_by_stage': fetch_reason_code_by_stage,
            'exact_case_counts': exact_case_counts,
            'readiness_reason_counts': readiness_reason_counts,
            'mismatch_code_counts': mismatch_code_counts,
            'basis_profile_counts': basis_profile_counts,
            'current_round_liquidity_event_count_counts': current_round_liquidity_event_count_counts,
            'current_round_trade_count_before_basis_counts': current_round_trade_count_before_basis_counts,
            'trade_count_between_basis_and_fee_free_basis_counts': trade_count_between_basis_and_fee_free_basis_counts,
            'exact_current_principal_case_counts': exact_current_principal_case_counts,
            'materialized_protocol_fee_split_case_counts': materialized_protocol_fee_split_case_counts,
            'protocol_fee_split_semantic_counts': protocol_fee_split_semantic_counts,
            'protocol_fee_split_timing_case_counts': protocol_fee_split_timing_case_counts,
            'unresolved_protocol_fee_timing_case_counts': unresolved_protocol_fee_timing_case_counts,
            'unresolved_protocol_fee_profile_counts': unresolved_protocol_fee_profile_counts,
            'unresolved_protocol_fee_semantic_counts': unresolved_protocol_fee_semantic_counts,
            'unresolved_protocol_fee_boundary_status_counts': unresolved_protocol_fee_boundary_status_counts,
            'unresolved_protocol_fee_explanation_counts': unresolved_protocol_fee_explanation_counts,
            'fee_to_continuity_case_counts': fee_to_continuity_case_counts,
            'protocol_fee_current_owner_provenance_case_counts': protocol_fee_current_owner_provenance_case_counts,
            'protocol_fee_current_owner_timing_case_counts': protocol_fee_current_owner_timing_case_counts,
            'safe_fee_to_restored_counts': safe_fee_to_restored_counts,
            'samples': samples,
        }

    def get_replay_transaction_audit(
        self,
        *,
        pool_id: int,
        pool_application: str,
        virtual_initial_liquidity: bool,
        start_id: int | None,
        end_id: int | None,
        swap_out_tolerance_attos: int,
    ):
        if swap_out_tolerance_attos < 0:
            raise ValueError('swap_out_tolerance_attos must be non-negative')

        pool_history_repository = self._position_metrics_dependencies().pool_history_repository()
        pool_transaction_history = pool_history_repository.get_pool_transaction_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        if start_id is not None or end_id is not None:
            lower_bound = int(start_id or 0)
            upper_bound = int(end_id or (2 ** 32 - 1))
            pool_transaction_history = [
                tx
                for tx in pool_transaction_history
                if lower_bound <= int(tx.get('transaction_id') or 0) <= upper_bound
            ]

        return {
            'pool_id': pool_id,
            'pool_application': pool_application,
            'virtual_initial_liquidity': virtual_initial_liquidity,
            'start_id': start_id,
            'end_id': end_id,
            'swap_out_tolerance_attos': swap_out_tolerance_attos,
            'audit': self._position_metrics_public_api.inspect_pool_history_replay(
                pool_transaction_history,
                virtual_initial_liquidity=virtual_initial_liquidity,
                swap_out_tolerance_attos=swap_out_tolerance_attos,
            ),
        }

    def get_diagnostics(
        self,
        *,
        source: str | None,
        owner: str | None,
        pool_application: str | None,
        pool_id: int | None,
        limit: int,
    ):
        if limit <= 0:
            raise ValueError('limit must be positive')
        return {
            'diagnostics': self._runtime.diagnostic_events_query_repository().get_diagnostic_events(
                source=source,
                owner=owner,
                pool_application=pool_application,
                pool_id=pool_id,
                limit=limit,
            ),
        }

    def get_debug_traces(
        self,
        *,
        source: str | None,
        component: str | None,
        operation: str | None,
        owner: str | None,
        pool_application: str | None,
        pool_id: int | None,
        start_at: int | None,
        end_at: int | None,
        limit: int,
    ):
        if limit <= 0:
            raise ValueError('limit must be positive')
        return {
            'traces': self._runtime.debug_traces_query_repository().get_debug_traces(
                source=source,
                component=component,
                operation=operation,
                owner=owner,
                pool_application=pool_application,
                pool_id=pool_id,
                start_at=start_at,
                end_at=end_at,
                limit=limit,
            ),
        }

    def get_debug_pool_bundle(
        self,
        *,
        pool_application: str,
        pool_id: int,
        owner: str | None,
        transaction_limit: int,
        diagnostics_limit: int,
    ):
        if transaction_limit <= 0 or diagnostics_limit <= 0:
            raise ValueError('limits must be positive')

        dependencies = self._position_metrics_dependencies()
        replay_facts_repository = dependencies.replay_facts_repository()
        snapshot_inputs_repository = dependencies.snapshot_inputs_repository()
        pool_history_repository = dependencies.pool_history_repository()

        transactions = pool_history_repository.get_pool_transaction_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        if len(transactions) > transaction_limit:
            transactions = transactions[-transaction_limit:]

        liquidity_history = []
        if owner is not None:
            replay_facts = replay_facts_repository.get_replay_facts(
                owner=owner,
                pool_application=pool_application,
                pool_id=pool_id,
                opened_at=None,
            )
            liquidity_history_source = replay_facts.liquidity_history
            if callable(liquidity_history_source):
                liquidity_history_source = liquidity_history_source()
            liquidity_history = list(liquidity_history_source)

        position_basis_snapshot = None
        pool_state_snapshot = None
        try:
            snapshot_inputs = snapshot_inputs_repository.get_snapshot_inputs(
                owner=owner,
                pool_application_id=pool_application,
                status='active',
            )
            snapshot_inputs = snapshot_inputs or {}
            position_basis_snapshot = snapshot_inputs.get('position_basis_snapshot')
            pool_state_snapshot = snapshot_inputs.get('pool_state_snapshot')
        except Exception:
            position_basis_snapshot = None
            pool_state_snapshot = None

        return {
            'pool_application': pool_application,
            'pool_id': pool_id,
            'owner': owner,
            'transaction_count': len(transactions),
            'transactions': transactions,
            'liquidity_history': liquidity_history,
            'gap_summary': pool_history_repository.get_pool_transaction_gap_summary(
                pool_application=pool_application,
                pool_id=pool_id,
            ),
            'diagnostics': self._runtime.diagnostic_events_query_repository().get_diagnostic_events(
                pool_application=pool_application,
                pool_id=pool_id,
                owner=owner,
                limit=diagnostics_limit,
            ),
            'position_basis_snapshot': position_basis_snapshot,
            'pool_state_snapshot': pool_state_snapshot,
        }

    @staticmethod
    def _int_or_zero(value: object) -> int:
        if value in (None, ''):
            return 0
        return int(value)

    def _protocol_fee_current_owner_timing_case(self, position_basis_snapshot: dict) -> str | None:
        basis_owned = self._int_or_zero(position_basis_snapshot.get('basis_protocol_fee_liquidity_owned_by_current_owner'))
        post_basis_owned = self._int_or_zero(position_basis_snapshot.get('post_basis_protocol_fee_liquidity_owned_by_current_owner'))
        post_basis_owned_before_first_add = self._int_or_zero(
            position_basis_snapshot.get('post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add')
        )
        if (
            basis_owned == 0
            and post_basis_owned == 0
            and post_basis_owned_before_first_add == 0
        ):
            return 'no_current_owner_protocol_fee'
        if post_basis_owned_before_first_add > post_basis_owned:
            return 'inconsistent_before_first_add_exceeds_post_basis'
        if basis_owned > 0 and post_basis_owned == 0:
            return 'basis_only'
        if basis_owned == 0 and post_basis_owned > 0:
            if post_basis_owned_before_first_add == post_basis_owned:
                return 'post_basis_only_before_first_add_only'
            return 'post_basis_only_with_later_add_present'
        if basis_owned > 0 and post_basis_owned > 0:
            if post_basis_owned_before_first_add == post_basis_owned:
                return 'basis_and_post_basis_before_first_add_only'
            return 'basis_and_post_basis_with_later_add_present'
        return 'unknown_or_partial'

    @staticmethod
    def _protocol_fee_unresolved_profile(
        *,
        materialized_protocol_fee_split_case: object,
        protocol_fee_current_owner_timing_case: object,
        fee_to_continuity_case: object,
        protocol_fee_current_owner_provenance_case: object,
    ) -> str | None:
        if materialized_protocol_fee_split_case != 'fee_to_nonzero_prior_add_basis_unresolved':
            return None
        return '|'.join([
            str(protocol_fee_current_owner_timing_case or 'unknown_timing'),
            str(fee_to_continuity_case or 'unknown_continuity'),
            str(protocol_fee_current_owner_provenance_case or 'unknown_provenance'),
        ])
