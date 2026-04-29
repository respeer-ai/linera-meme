from fastapi import FastAPI, Request, WebSocket, Query
from fastapi.responses import JSONResponse
import asyncio
import uvicorn
import argparse
import traceback
import time
import async_request
from environment import running_in_k8s
import position_metrics


from swap import Swap
from subscription import WebSocketManager
from ticker import Ticker
from db import Db, align_timestamp_to_minute_ms
from request_trace import build_api_request_log_line, build_api_trace_context
from storage.mysql.projection_repo import ProjectionRepository
from storage.mysql.position_metrics_diagnostic_recorder import PositionMetricsDiagnosticRecorder
from storage.mysql.position_metrics_projection_repo import PositionMetricsProjectionRepository
from query.read_models.candles import CandlesReadModel
from query.read_models.live_position_metrics_fetcher import LivePositionMetricsFetcher
from query.read_models.transactions import TransactionsReadModel
from query.read_models.positions import PositionsReadModel
from query.read_models.position_metrics import PositionMetricsReadModel
from query.read_models.position_metrics_snapshot_fast_path import PositionMetricsSnapshotFastPath
from query.read_models.position_metrics_protocol_fee_split_semantics import PositionMetricsProtocolFeeSplitSemantics
from query.read_models.position_metrics_snapshot_shadow_evaluator import PositionMetricsSnapshotShadowEvaluator
from query.handlers.kline import KlineHandler
from query.handlers.transactions import TransactionsHandler
from query.handlers.positions import PositionsHandler
from query.handlers.position_metrics import PositionMetricsHandler
from query.handlers.priority_one_rollout import PriorityOneRollout
from query.serializers.kline import KlineSerializer
from query.serializers.transactions import TransactionsSerializer
from query.serializers.positions import PositionsSerializer
from query.serializers.position_metrics import PositionMetricsSerializer
from app.observability_facade import ObservabilityFacade
from app.observability_supervisor import ObservabilitySupervisor
from app.observability_runtime import ObservabilityRuntime
from app.config import KlineAppConfig
from integration.pool_application_client import PoolApplicationClient


app = FastAPI()
_swap = None
manager = None
_ticker = None
_ticker_task = None
_db = None
_ticker_db = None
_db_config = None
_observability_config = None
_observability_supervisor = None
_observability_facade = None
_position_metrics_protocol_fee_split_semantics = PositionMetricsProtocolFeeSplitSemantics()


def _protocol_fee_current_owner_timing_case(position_basis_snapshot: dict) -> str | None:
    basis_owned = _int_or_zero(position_basis_snapshot.get('basis_protocol_fee_liquidity_owned_by_current_owner'))
    post_basis_owned = _int_or_zero(position_basis_snapshot.get('post_basis_protocol_fee_liquidity_owned_by_current_owner'))
    post_basis_owned_before_first_add = _int_or_zero(
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


def _int_or_zero(value: object) -> int:
    if value in (None, ''):
        return 0
    return int(value)


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


def _build_priority1_rollout() -> PriorityOneRollout:
    return PriorityOneRollout(_db)


def _build_projection_repository():
    if _db is None:
        raise RuntimeError('Db client is not initialized')
    return ProjectionRepository(_db)


def _build_position_metrics_repository():
    if _db is None:
        raise RuntimeError('Db client is not initialized')
    return PositionMetricsProjectionRepository(_db)


def _build_kline_handler() -> KlineHandler:
    repository = _build_projection_repository()
    return KlineHandler(CandlesReadModel(repository), KlineSerializer())


def _build_transactions_handler() -> TransactionsHandler:
    repository = _build_projection_repository()
    return TransactionsHandler(TransactionsReadModel(repository), TransactionsSerializer())


def _build_positions_handler() -> PositionsHandler:
    repository = _build_projection_repository()
    return PositionsHandler(PositionsReadModel(repository), PositionsSerializer())


def _build_position_metrics_handler() -> PositionMetricsHandler:
    repository = _build_position_metrics_repository()

    async def default_fetcher(position: dict):
        return await _build_position_metrics_fetcher(repository)(position)

    fetcher = _position_metrics_fetcher or default_fetcher
    return PositionMetricsHandler(
        PositionMetricsReadModel(repository, fetcher),
        PositionMetricsSerializer(),
        PositionMetricsDiagnosticRecorder(_db),
    )


async def _build_position_metrics_readiness_debug_payload(
    *,
    owner: str,
    status: str,
    sample_limit: int,
):
    repository = _build_position_metrics_repository()

    async def default_fetcher(position: dict):
        return await _build_position_metrics_fetcher(repository)(position)

    fetcher = _position_metrics_fetcher or default_fetcher
    payload = await PositionMetricsReadModel(repository, fetcher).get_position_metrics(
        owner=owner,
        status=status,
    )
    shadow_diagnostics = list(payload.pop('_shadow_diagnostics', []) or [])
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
        shadow = (shadow_row or {}).get('snapshot_shadow') or {}
        readiness = str(shadow.get('readiness') or 'shadow_unavailable')
        if readiness not in readiness_counts:
            readiness_counts[readiness] = 0
        readiness_counts[readiness] += 1
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
        protocol_fee_split_semantic = _position_metrics_protocol_fee_split_semantics.semantic_for_case(
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
        protocol_fee_current_owner_timing_case = _protocol_fee_current_owner_timing_case(position_basis_snapshot)
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
        unresolved_protocol_fee_profile = _protocol_fee_unresolved_profile(
            materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
            protocol_fee_current_owner_timing_case=protocol_fee_current_owner_timing_case,
            fee_to_continuity_case=fee_to_continuity_case,
            protocol_fee_current_owner_provenance_case=protocol_fee_current_owner_provenance_case,
        )
        if unresolved_protocol_fee_profile not in (None, ''):
            unresolved_protocol_fee_profile_counts[unresolved_protocol_fee_profile] = (
                unresolved_protocol_fee_profile_counts.get(unresolved_protocol_fee_profile, 0) + 1
            )
        unresolved_protocol_fee_semantic = _position_metrics_protocol_fee_split_semantics.unresolved_semantic(
            unresolved_protocol_fee_profile
        )
        unresolved_protocol_fee_explanation = _position_metrics_protocol_fee_split_semantics.unresolved_explanation(
            unresolved_protocol_fee_semantic
        )
        unresolved_protocol_fee_boundary_status = _position_metrics_protocol_fee_split_semantics.unresolved_boundary_status(
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
        safe_fee_to_restored = _position_metrics_protocol_fee_split_semantics.is_safe_restored_case(
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
                'metrics_status': metric.get('metrics_status'),
                'exact_fee_supported': bool(metric.get('exact_fee_supported')),
                'exact_principal_supported': bool(metric.get('exact_principal_supported')),
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


def _get_kline_legacy(
    *,
    token_0: str,
    token_1: str,
    start_at: int,
    end_at: int,
    interval: str,
    pool_id: int | None = None,
    pool_application: str | None = None,
) -> dict:
    response_pool_id, response_pool_application, resolved_token_0, resolved_token_1, points = _db.get_kline(
        token_0=token_0,
        token_1=token_1,
        start_at=start_at,
        end_at=end_at,
        interval=interval,
        pool_id=pool_id,
        pool_application=pool_application,
    )
    return {
        'pool_id': response_pool_id,
        'pool_application': response_pool_application,
        'token_0': resolved_token_0,
        'token_1': resolved_token_1,
        'interval': interval,
        'start_at': start_at,
        'end_at': end_at,
        'points': points,
    }


def _get_kline_information_legacy(
    *,
    token_0: str,
    token_1: str,
    interval: str,
    pool_id: int | None = None,
    pool_application: str | None = None,
):
    return _db.get_kline_information(
        token_0=token_0,
        token_1=token_1,
        interval=interval,
        pool_id=pool_id,
        pool_application=pool_application,
    )


def _get_transactions_legacy(
    *,
    token_0: str | None,
    token_1: str | None,
    start_at: int,
    end_at: int,
):
    return _db.get_transactions(
        token_0=token_0,
        token_1=token_1,
        start_at=start_at,
        end_at=end_at,
    )


def _get_transactions_information_legacy(
    *,
    token_0: str | None,
    token_1: str | None,
):
    return _db.get_transactions_information(token_0=token_0, token_1=token_1)


def _get_positions_legacy(
    *,
    owner: str,
    status: str,
):
    return {
        'owner': owner,
        'positions': _db.get_positions(owner=owner, status=status),
    }


def _build_position_metrics_fetcher(repository) -> LivePositionMetricsFetcher:
    if _swap is None:
        raise RuntimeError('Swap client is not initialized')
    return LivePositionMetricsFetcher(
        repository=repository,
        pool_application_client=PoolApplicationClient(
            base_url=_swap.base_url,
            post=async_request.post,
            in_k8s=running_in_k8s(),
        ),
        parse_owner_account=position_metrics.parse_account,
        enrich_payload=position_metrics.enrich_position_metrics_from_payload,
        snapshot_fast_path=PositionMetricsSnapshotFastPath(),
        snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
    )


_position_metrics_fetcher = None


async def _fetch_live_pool_transaction_ids(
    pool_application: str,
    *,
    recent_window: int,
):
    if _swap is None:
        raise RuntimeError('Swap client is not initialized')

    url = position_metrics.pool_application_url(
        _swap.base_url,
        pool_application,
        in_k8s=running_in_k8s(),
    )
    response = await async_request.post(
        url=url,
        json={'query': 'query {\n latestTransactions \n}'},
        timeout=(3, 10),
    )
    response.raise_for_status()
    payload = response.json()
    if 'errors' in payload:
        raise RuntimeError(str(payload['errors']))

    latest_transactions = payload['data']['latestTransactions'] or []
    latest_ids = sorted(
        int(transaction['transactionId'])
        for transaction in latest_transactions
        if transaction.get('transactionId') is not None
    )
    if recent_window > 0 and len(latest_ids) > recent_window:
        latest_ids = latest_ids[-recent_window:]
    return latest_ids


async def _build_recent_transaction_window_audit(
    *,
    pool_id: int,
    pool_application: str,
    recent_window: int,
):
    if _db is None:
        raise RuntimeError('Db client is not initialized')
    if recent_window <= 0:
        raise ValueError('recent_window must be positive')

    live_ids = await _fetch_live_pool_transaction_ids(
        pool_application,
        recent_window=recent_window,
    )
    if not live_ids:
        return {
            'pool_id': pool_id,
            'pool_application': pool_application,
            'recent_window': recent_window,
            'window_start_id': None,
            'window_end_id': None,
            'live_ids': [],
            'db_ids': [],
            'missing_in_db': [],
            'missing_in_live': [],
        }

    window_start_id = live_ids[0]
    window_end_id = live_ids[-1]
    db_ids = _db.get_pool_transaction_ids(
        pool_id=pool_id,
        pool_application=pool_application,
        start_id=window_start_id,
        end_id=window_end_id,
    )
    live_id_set = set(live_ids)
    db_id_set = set(db_ids)

    return {
        'pool_id': pool_id,
        'pool_application': pool_application,
        'recent_window': recent_window,
        'window_start_id': window_start_id,
        'window_end_id': window_end_id,
        'live_ids': live_ids,
        'db_ids': db_ids,
        'missing_in_db': sorted(live_id_set - db_id_set),
        'missing_in_live': sorted(db_id_set - live_id_set),
    }


def _build_observability_supervisor():
    if _observability_config is None:
        return ObservabilitySupervisor(None)
    required_keys = {
        'database_host',
        'database_port',
        'database_name',
        'database_username',
        'database_password',
        'chain_graphql_url',
    }
    if not required_keys.issubset(set(_observability_config.keys())):
        return ObservabilitySupervisor(None)
    runtime = ObservabilityRuntime(KlineAppConfig(**_observability_config))
    return ObservabilitySupervisor(runtime)


@app.get('/transactions/audit/recent')
async def on_get_recent_transaction_audit(
    pool_id: int = Query(...),
    pool_application: str = Query(...),
    recent_window: int = Query(default=5000),
):
    try:
        return await _build_recent_transaction_window_audit(
            pool_id=pool_id,
            pool_application=pool_application,
            recent_window=recent_window,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed audit recent transactions: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/transactions/audit/replay')
async def on_get_replay_transaction_audit(
    pool_id: int = Query(...),
    pool_application: str = Query(...),
    virtual_initial_liquidity: bool = Query(default=False),
    start_id: int | None = Query(default=None),
    end_id: int | None = Query(default=None),
    swap_out_tolerance_attos: int = Query(default=1),
):
    try:
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if swap_out_tolerance_attos < 0:
            raise ValueError('swap_out_tolerance_attos must be non-negative')

        pool_transaction_history = _db.get_pool_transaction_history(
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
            'audit': position_metrics.inspect_pool_history_replay(
                pool_transaction_history,
                virtual_initial_liquidity=virtual_initial_liquidity,
                swap_out_tolerance_attos=swap_out_tolerance_attos,
            ),
        }
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed replay transaction audit: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/points/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}/interval/{interval}')
async def on_get_kline(
    request: Request,
    token0: str,
    token1: str,
    start_at: int,
    end_at: int,
    interval: str,
    pool_id: int | None = Query(default=None),
    pool_application: str | None = Query(default=None),
):
    token_0 = token0
    token_1 = token1
    response_pool_id = pool_id
    response_pool_application = pool_application
    points = []
    raw_start_at = start_at
    raw_end_at = end_at
    request_id = request.query_params.get('request_id')
    trace = build_api_trace_context(request_id, raw_start_at, raw_end_at, interval)
    handler_started_at = time.perf_counter()

    # TODO: align to needed interval
    start_at = align_timestamp_to_minute_ms(start_at)
    end_at = align_timestamp_to_minute_ms(end_at)
    print(build_api_request_log_line(
        'received',
        aligned_end_at=end_at,
        aligned_start_at=start_at,
        client_sent_at_ms=request.query_params.get('client_sent_at_ms') or 'missing',
        interval=interval,
        raw_end_at=trace['raw_end_at'],
        raw_start_at=trace['raw_start_at'],
        received_at_ms=trace['received_at_ms'],
        request_id=trace['request_id'],
    ))

    try:
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            payload = _get_kline_legacy(
                token_0=token0,
                token_1=token1,
                start_at=start_at,
                end_at=end_at,
                interval=interval,
                pool_id=pool_id,
                pool_application=pool_application,
            )
        else:
            payload = _build_kline_handler().get_points(
                token_0=token0,
                token_1=token1,
                start_at=start_at,
                end_at=end_at,
                interval=interval,
                pool_id=pool_id,
                pool_application=pool_application,
            )
            legacy_payload = _get_kline_legacy(
                token_0=token0,
                token_1=token1,
                start_at=start_at,
                end_at=end_at,
                interval=interval,
                pool_id=pool_id,
                pool_application=pool_application,
            )
            rollout.compare(
                endpoint='/points',
                legacy_payload=legacy_payload,
                new_payload=payload,
                pool_application=payload['pool_application'],
                pool_id=payload['pool_id'],
            )
        response_pool_id = payload['pool_id']
        response_pool_application = payload['pool_application']
        token_0 = payload['token_0']
        token_1 = payload['token_1']
        points = payload['points']
    except Exception as e:
        print(f'Failed get kline: {e}')
    finally:
        print(build_api_request_log_line(
            'completed',
            aligned_end_at=end_at,
            aligned_start_at=start_at,
            duration_ms=int((time.perf_counter() - handler_started_at) * 1000),
            point_count=len(points),
            request_id=trace['request_id'],
        ))

    return {
        'pool_id': response_pool_id,
        'pool_application': response_pool_application,
        'token_0': token_0,
        'token_1': token_1,
        'interval': interval,
        'start_at': start_at,
        'end_at': end_at,
        'points': points,
    }


@app.get('/points/token0/{token0}/token1/{token1}/interval/{interval}/information')
async def on_get_kline_information(
    token0: str,
    token1: str,
    interval: str,
    pool_id: int | None = Query(default=None),
    pool_application: str | None = Query(default=None),
):
    try:
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            return _get_kline_information_legacy(
                token_0=token0,
                token_1=token1,
                interval=interval,
                pool_id=pool_id,
                pool_application=pool_application,
            )
        payload = _build_kline_handler().get_information(
            token_0=token0,
            token_1=token1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        legacy_payload = _get_kline_information_legacy(
            token_0=token0,
            token_1=token1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        rollout.compare(
            endpoint='/points/information',
            legacy_payload=legacy_payload,
            new_payload=payload,
            pool_application=pool_application,
            pool_id=pool_id,
        )
        return payload
    except Exception as e:
        print(f'Failed get kline information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/transactions/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}')
async def on_get_transactions(token0: str, token1: str, start_at: int, end_at: int):
    rollout = _build_priority1_rollout()
    if rollout.use_legacy():
        return _get_transactions_legacy(
            token_0=token0,
            token_1=token1,
            start_at=start_at,
            end_at=end_at,
        )
    payload = _build_transactions_handler().get_transactions(
        token_0=token0,
        token_1=token1,
        start_at=start_at,
        end_at=end_at,
    )
    legacy_payload = _get_transactions_legacy(
        token_0=token0,
        token_1=token1,
        start_at=start_at,
        end_at=end_at,
    )
    rollout.compare(
        endpoint='/transactions',
        legacy_payload=legacy_payload,
        new_payload=payload,
    )
    return payload


@app.get('/transactions/start_at/{start_at}/end_at/{end_at}')
async def on_get_combined_transactions(start_at: int, end_at: int):
    rollout = _build_priority1_rollout()
    if rollout.use_legacy():
        return _get_transactions_legacy(
            token_0=None,
            token_1=None,
            start_at=start_at,
            end_at=end_at,
        )
    payload = _build_transactions_handler().get_transactions(
        token_0=None,
        token_1=None,
        start_at=start_at,
        end_at=end_at,
    )
    legacy_payload = _get_transactions_legacy(
        token_0=None,
        token_1=None,
        start_at=start_at,
        end_at=end_at,
    )
    rollout.compare(
        endpoint='/transactions/combined',
        legacy_payload=legacy_payload,
        new_payload=payload,
    )
    return payload


@app.get('/transactions/token0/{token0}/token1/{token1}/information')
async def on_get_transactions_information(token0: str, token1: str):
    try:
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            return _get_transactions_information_legacy(token_0=token0, token_1=token1)
        payload = _build_transactions_handler().get_information(token_0=token0, token_1=token1)
        legacy_payload = _get_transactions_information_legacy(token_0=token0, token_1=token1)
        rollout.compare(
            endpoint='/transactions/information',
            legacy_payload=legacy_payload,
            new_payload=payload,
        )
        return payload
    except Exception as e:
        print(f'Failed get transactions information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/transactions/information')
async def on_get_combined_transactions_information():
    try:
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            return _get_transactions_information_legacy(token_0=None, token_1=None)
        payload = _build_transactions_handler().get_information(token_0=None, token_1=None)
        legacy_payload = _get_transactions_information_legacy(token_0=None, token_1=None)
        rollout.compare(
            endpoint='/transactions/information/combined',
            legacy_payload=legacy_payload,
            new_payload=payload,
        )
        return payload
    except Exception as e:
        print(f'Failed get transactions information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/positions')
async def on_get_positions(
    owner: str = Query(...),
    status: str = Query(default='active'),
):
    try:
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            return _get_positions_legacy(owner=owner, status=status)
        payload = _build_positions_handler().get_positions(owner=owner, status=status)
        legacy_payload = _get_positions_legacy(owner=owner, status=status)
        rollout.compare(
            endpoint='/positions',
            legacy_payload=legacy_payload,
            new_payload=payload,
            owner=owner,
            status=status,
        )
        return payload
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get positions: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/position-metrics')
async def on_get_position_metrics(
    owner: str = Query(...),
    status: str = Query(default='active'),
):
    try:
        return await _build_position_metrics_handler().get_position_metrics(
            owner=owner,
            status=status,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get position metrics: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/position-metrics/readiness')
async def on_get_position_metrics_readiness_debug(
    owner: str = Query(...),
    status: str = Query(default='active'),
    sample_limit: int = Query(default=100),
):
    try:
        if sample_limit <= 0:
            raise ValueError('sample_limit must be positive')
        return await _build_position_metrics_readiness_debug_payload(
            owner=owner,
            status=status,
            sample_limit=sample_limit,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get position metrics readiness debug: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/diagnostics')
async def on_get_diagnostics(
    source: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    pool_application: str | None = Query(default=None),
    pool_id: int | None = Query(default=None),
    limit: int = Query(default=200),
):
    try:
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if limit <= 0:
            raise ValueError('limit must be positive')
        return {
            'diagnostics': _db.get_diagnostic_events(
                source=source,
                owner=owner,
                pool_application=pool_application,
                pool_id=pool_id,
                limit=limit,
            ),
        }
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get diagnostics: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/priority1-rollout')
async def on_get_debug_priority1_rollout(
    limit: int = Query(default=20),
):
    try:
        if limit <= 0:
            raise ValueError('limit must be positive')
        return _build_priority1_rollout().status(limit=limit)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get priority1 rollout debug: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/traces')
async def on_get_debug_traces(
    source: str | None = Query(default=None),
    component: str | None = Query(default=None),
    operation: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    pool_application: str | None = Query(default=None),
    pool_id: int | None = Query(default=None),
    start_at: int | None = Query(default=None),
    end_at: int | None = Query(default=None),
    limit: int = Query(default=200),
):
    try:
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if limit <= 0:
            raise ValueError('limit must be positive')

        return {
            'traces': _db.get_debug_traces(
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
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get debug traces: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/pool')
async def on_get_debug_pool_bundle(
    pool_application: str = Query(...),
    pool_id: int = Query(...),
    owner: str | None = Query(default=None),
    transaction_limit: int = Query(default=1000),
    diagnostics_limit: int = Query(default=200),
    include_live_recent: bool = Query(default=False),
    recent_window: int = Query(default=5000),
):
    try:
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if transaction_limit <= 0 or diagnostics_limit <= 0:
            raise ValueError('limits must be positive')
        if recent_window <= 0:
            raise ValueError('recent_window must be positive')

        transactions = _db.get_pool_transaction_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        if len(transactions) > transaction_limit:
            transactions = transactions[-transaction_limit:]

        liquidity_history = []
        if owner is not None:
            liquidity_history = _db.get_position_liquidity_history(
                owner=owner,
                pool_application=pool_application,
                pool_id=pool_id,
            )

        live_recent_audit = None
        if include_live_recent:
            live_recent_audit = await _build_recent_transaction_window_audit(
                pool_id=pool_id,
                pool_application=pool_application,
                recent_window=recent_window,
            )

        position_basis_snapshot = None
        pool_state_snapshot = None
        try:
            position_metrics_repository = _build_position_metrics_repository()
            pool_state_snapshot = position_metrics_repository.get_pool_state_snapshot(
                pool_application_id=pool_application,
            )
            if owner is not None:
                position_basis_snapshot = position_metrics_repository.get_position_basis_snapshot(
                    owner=owner,
                    pool_application_id=pool_application,
                    status='active',
                )
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
            'gap_summary': _db.get_pool_transaction_gap_summary(
                pool_application=pool_application,
                pool_id=pool_id,
            ),
            'diagnostics': _db.get_diagnostic_events(
                pool_application=pool_application,
                pool_id=pool_id,
                owner=owner,
                limit=diagnostics_limit,
            ),
            'position_basis_snapshot': position_basis_snapshot,
            'pool_state_snapshot': pool_state_snapshot,
            'live_recent_audit': live_recent_audit,
        }
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get debug pool bundle: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post('/debug/catch-up/run')
async def on_post_debug_catch_up_run(
    chain_id: str | None = Query(default=None),
    max_blocks: int | None = Query(default=None),
):
    try:
        if max_blocks is not None and max_blocks <= 0:
            raise ValueError('max_blocks must be positive')
        if _observability_facade is None:
            raise RuntimeError('Observability runtime is not configured')
        return await _observability_facade.run_catch_up(
            chain_id=chain_id,
            max_blocks=max_blocks,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed run debug catch-up: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post('/debug/normalization/replay/run')
async def on_post_debug_normalization_replay_run(
    raw_table: str | None = Query(default=None),
    batch_limit: int | None = Query(default=None),
    max_batches: int | None = Query(default=None),
    reprocess_reason: str | None = Query(default=None),
):
    try:
        if batch_limit is not None and batch_limit <= 0:
            raise ValueError('batch_limit must be positive')
        if max_batches is not None and max_batches <= 0:
            raise ValueError('max_batches must be positive')
        if raw_table is not None and raw_table not in {'raw_operations', 'raw_posted_messages'}:
            raise ValueError('raw_table must be one of raw_operations, raw_posted_messages')
        if _observability_facade is None:
            raise RuntimeError('Observability runtime is not configured')
        return await _observability_facade.run_normalization_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed run debug normalization replay: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post('/debug/market-derivation/replay/run')
async def on_post_debug_market_derivation_replay_run(
    raw_table: str | None = Query(default=None),
    batch_limit: int | None = Query(default=None),
    max_batches: int | None = Query(default=None),
    reprocess_reason: str | None = Query(default=None),
):
    try:
        if batch_limit is not None and batch_limit <= 0:
            raise ValueError('batch_limit must be positive')
        if max_batches is not None and max_batches <= 0:
            raise ValueError('max_batches must be positive')
        if raw_table is not None and raw_table not in {'raw_posted_messages'}:
            raise ValueError('raw_table must be one of raw_posted_messages')
        if _observability_facade is None:
            raise RuntimeError('Observability runtime is not configured')
        return await _observability_facade.run_market_derivation_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed run debug market derivation replay: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/observability')
async def on_get_debug_observability(
    chain_ids: str | None = Query(default=None),
    run_statuses: str | None = Query(default=None),
    anomaly_statuses: str | None = Query(default=None),
    limit: int = Query(default=200),
):
    try:
        if limit <= 0:
            raise ValueError('limit must be positive')

        parsed_chain_ids = tuple(
            chain_id.strip()
            for chain_id in (chain_ids or '').split(',')
            if chain_id.strip()
        )
        parsed_run_statuses = tuple(
            status.strip()
            for status in (run_statuses or '').split(',')
            if status.strip()
        )
        parsed_anomaly_statuses = tuple(
            status.strip()
            for status in (anomaly_statuses or '').split(',')
            if status.strip()
        )

        if _observability_facade is None:
            return {
                'status': {
                    'configured': False,
                    'state': 'disabled',
                    'ready': False,
                    'last_error': 'observability is not configured',
                    'last_transition_at': None,
                    'starting_in_background': False,
                    'components': {},
                },
                'chain_ids': list(parsed_chain_ids),
                'run_statuses': list(parsed_run_statuses),
                'anomaly_statuses': list(parsed_anomaly_statuses),
                'cursors': [],
                'recent_runs': [],
                'anomalies': [],
            }
        return _observability_facade.get_debug_observability(
            chain_ids=parsed_chain_ids,
            run_statuses=parsed_run_statuses,
            anomaly_statuses=parsed_anomaly_statuses,
            limit=limit,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get debug observability: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post('/debug/observability/recover')
async def on_post_debug_observability_recover():
    try:
        if _observability_facade is None:
            return {
                'recovered': False,
                'status': {
                    'configured': False,
                    'state': 'disabled',
                    'ready': False,
                    'last_error': 'observability is not configured',
                    'last_transition_at': None,
                    'starting_in_background': False,
                    'recovery_allowed': False,
                    'components': {},
                },
            }
        return await _observability_facade.recover()
    except Exception as e:
        print(f'Failed recover observability: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/ticker/interval/{interval}')
async def on_get_ticker(interval: str):
    try:
        stats =  _db.get_ticker(interval=interval)
        return {
            'interval': interval,
            'stats': stats,
        }
    except Exception as e:
        print(f'Failed get ticker: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get('/poolstats/interval/{interval}')
async def on_get_pool_stats(interval: str):
    try:
        stats =  _db.get_pool_stats(interval=interval)
        return {
            'interval': interval,
            'stats': stats,
        }
    except Exception as e:
        print(f'Failed get ticker: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get('/protocol/stats')
async def get_protocol_stats() -> dict:
    try:
        pools = await _swap.get_pools()
        stats = _db.get_protocol_stats(pools)
        return stats
    except Exception as e:
        print(f'Failed get protocol stats: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.websocket('/ws')
async def on_subscribe(websocket: WebSocket):
    await websocket.accept()
    await manager.connect(websocket)

async def run_ticker_forever():
    global _ticker
    while _ticker is not None and _ticker.running():
        try:
            await _ticker.run()
        except Exception as e:
            print(f'Ticker quiting ... {e}')
            traceback.print_exc()
            await asyncio.sleep(10)


@app.on_event('startup')
async def on_startup():
    global _ticker, _ticker_task, _ticker_db
    if _swap is None or manager is None or _db_config is None:
        return
    if _ticker_task is not None:
        return

    _ticker_db = Db(
        _db_config['host'],
        _db_config['port'],
        _db_config['db_name'],
        _db_config['username'],
        _db_config['password'],
        False,
    )
    _ticker = Ticker(manager, _swap, _ticker_db)
    _ticker_task = asyncio.create_task(run_ticker_forever())
    if _observability_supervisor is not None:
        _observability_supervisor.start_in_background()


@app.on_event('shutdown')
async def on_shutdown():
    global _ticker_task
    if _ticker is not None:
        _ticker.stop()
    if _ticker_task is not None:
        await _ticker_task
        _ticker_task = None
    if _ticker_db is not None:
        _ticker_db.close()
    if _observability_supervisor is not None:
        await _observability_supervisor.shutdown()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Swap Kline')

    parser.add_argument('--host', type=str, default='0.0.0.0', help='Listened ip')
    parser.add_argument('--port', type=int, default=25080, help='Listened port')
    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--swap-chain-id', type=str, required=True, help='Swap chain id')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--proxy-host', type=str, default='', help='Host of proxy service')
    parser.add_argument('--proxy-chain-id', type=str, default='', help='Proxy chain id')
    parser.add_argument('--proxy-application-id', type=str, default='', help='Proxy application id')
    parser.add_argument('--database-host', type=str, default='localhost', help='Kline database host')
    parser.add_argument('--database-port', type=str, default='3306', help='Kline database port')
    parser.add_argument('--database-user', type=str, default='debian-sys-maint ', help='Kline database user')
    parser.add_argument('--database-password', type=str, default='4EwQJrNprvw8McZm', help='Kline database password')
    parser.add_argument('--database-name', type=str, default='linera_swap_kline', help='Kline database name')
    parser.add_argument('--clean-kline', action='store_true', help='Clean kline database')
    parser.add_argument('--chain-graphql-url', type=str, default='', help='Linera node service GraphQL URL for raw block ingestion')
    parser.add_argument('--chain-graphql-ws-url', type=str, default='', help='Optional Linera node service GraphQL WebSocket URL for notifications')
    parser.add_argument('--catch-up-chain-ids', type=str, default='', help='Comma-separated chain ids for event-driven/admin catch-up')
    parser.add_argument('--catch-up-max-blocks-per-chain', type=int, default=50, help='Bounded catch-up block limit per chain run')
    parser.add_argument('--disable-catch-up-on-startup', action='store_true', help='Disable startup reconciliation catch-up for configured chains')
    parser.add_argument('--notification-reconnect-delay-seconds', type=float, default=1.0, help='Reconnect backoff in seconds for Linera notification subscriptions')

    args = parser.parse_args()

    _db_config = {
        'host': args.database_host,
        'port': args.database_port,
        'db_name': args.database_name,
        'username': args.database_user,
        'password': args.database_password,
    }
    parsed_catch_up_chain_ids = tuple(
        chain_id.strip()
        for chain_id in args.catch_up_chain_ids.split(',')
        if chain_id.strip()
    )
    if args.chain_graphql_url:
        _observability_config = {
            'database_host': args.database_host,
            'database_port': args.database_port,
            'database_name': args.database_name,
            'database_username': args.database_user,
            'database_password': args.database_password,
            'chain_graphql_url': args.chain_graphql_url,
            'chain_graphql_ws_url': args.chain_graphql_ws_url or None,
            'catch_up_chain_ids': parsed_catch_up_chain_ids,
            'catch_up_max_blocks_per_chain': args.catch_up_max_blocks_per_chain,
            'catch_up_on_startup': not args.disable_catch_up_on_startup,
            'notification_reconnect_delay_seconds': args.notification_reconnect_delay_seconds,
            'swap_host': args.swap_host,
            'swap_chain_id': args.swap_chain_id,
            'swap_application_id': args.swap_application_id,
            'proxy_host': args.proxy_host or None,
            'proxy_chain_id': args.proxy_chain_id or None,
            'proxy_application_id': args.proxy_application_id or None,
        }
    _observability_supervisor = _build_observability_supervisor()
    _observability_facade = ObservabilityFacade(_observability_supervisor)

    _db = Db(args.database_host, args.database_port, args.database_name, args.database_user, args.database_password, args.clean_kline)
    _swap = Swap(args.swap_host, args.swap_chain_id, args.swap_application_id, None, db=_db)
    manager = WebSocketManager(_swap, _db)

    uvicorn.run(app, host=args.host, port=args.port, ws_ping_interval=30, ws_ping_timeout=10)

    if _db is not None:
        _db.close()
