import async_request
from environment import running_in_k8s
from decimal import Decimal
from position_metrics_fee_free_open_state_simulator import PositionMetricsFeeFreeOpenStateSimulator
from position_metrics_facade_support import PositionMetricsFacadeSupport
from position_metrics_history_enricher import PositionMetricsHistoryEnricher
from position_metrics_liquidity_history_analyzer import PositionMetricsLiquidityHistoryAnalyzer
from position_metrics_liquidity_history_support import PositionMetricsLiquidityHistorySupport
from position_metrics_live_history_reconciler import PositionMetricsLiveHistoryReconciler
from position_metrics_partial_result_builder import PositionMetricsPartialResultBuilder
from position_metrics_payload_enricher import PositionMetricsPayloadEnricher
from position_metrics_pool_application_support import PositionMetricsPoolApplicationSupport
from position_metrics_pool_history_reconstructor import PositionMetricsPoolHistoryReconstructor
from position_metrics_pool_history_replay_inspector import PositionMetricsPoolHistoryReplayInspector
from position_metrics_replay_support import PositionMetricsReplaySupport
from position_metrics_swap_history_exactness_solver import PositionMetricsSwapHistoryExactnessSolver
from position_metrics_swap_math_support import PositionMetricsSwapMathSupport
from position_metrics_swap_support import PositionMetricsSwapSupport
from position_metrics_transaction_history_support import PositionMetricsTransactionHistorySupport
from position_metrics_value_support import PositionMetricsValueSupport
from position_metrics_warning_applier import PositionMetricsWarningApplier

EPSILON = Decimal('0.000000000001')
DISPLAY_QUANTUM = Decimal('0.000000000000000001')
ATTOS_SCALE = 10 ** 18
LIQUIDITY_MINT_TOLERANCE_ATTOS = 100
SWAP_OUT_TOLERANCE_ATTOS = 1
SWAP_FEE_NUMERATOR = 997
SWAP_FEE_DENOMINATOR = 1000

def parse_account(account: str):
    return _pool_application_support().parse_account(account)


def pool_application_url(base_url: str, pool_application: str, in_k8s: bool | None = None):
    return _pool_application_support().pool_application_url(
        base_url,
        pool_application,
        in_k8s=in_k8s,
    )


def build_position_metrics_query(owner: dict):
    return _pool_application_support().build_position_metrics_query(owner)


def build_position_metrics_legacy_query(owner: dict):
    return _pool_application_support().build_position_metrics_legacy_query(owner)


def _graphql_unknown_field(payload: dict, field_name: str) -> bool:
    return _pool_application_support().graphql_unknown_field(payload, field_name)


def _to_decimal(value):
    return _value_support().to_decimal(value)


def _pool_application_support() -> PositionMetricsPoolApplicationSupport:
    return PositionMetricsPoolApplicationSupport(
        running_in_k8s=running_in_k8s,
    )


def _serialize_decimal(value: Decimal | None):
    return _value_support().serialize_decimal(value)


def _account_payload_to_string(account: dict | None) -> str | None:
    if not isinstance(account, dict):
        return None
    chain_id = account.get('chain_id')
    owner = account.get('owner')
    if chain_id is None or owner is None:
        return None
    return f'{chain_id}:{owner}'


def _normalize_live_transaction(tx: dict) -> dict:
    return _transaction_history_support().normalize_live_transaction(tx)


def _merge_transaction_history(
    persisted_history: list[dict] | None,
    live_history: list[dict] | None,
) -> list[dict]:
    return _transaction_history_support().merge_transaction_history(
        persisted_history,
        live_history,
    )


def _build_transaction_gap_summary(
    transaction_history: list[dict] | None,
    *,
    start_id: int | None = None,
    end_id: int | None = None,
    sample_limit: int = 8,
) -> dict:
    return _transaction_history_support().build_transaction_gap_summary(
        transaction_history,
        start_id=start_id,
        end_id=end_id,
        sample_limit=sample_limit,
    )


def _transaction_history_support() -> PositionMetricsTransactionHistorySupport:
    return PositionMetricsTransactionHistorySupport(
        account_payload_to_string=_account_payload_to_string,
    )


def _to_attos(value) -> int | None:
    return _value_support().to_attos(value)


def _from_attos(value: int | None) -> Decimal | None:
    return _value_support().from_attos(value)


def _attos_within_tolerance(left: int, right: int, tolerance: int = LIQUIDITY_MINT_TOLERANCE_ATTOS) -> bool:
    return _value_support().attos_within_tolerance(left, right, tolerance)

def _swap_out_within_tolerance(left: int, right: int, tolerance: int = SWAP_OUT_TOLERANCE_ATTOS) -> bool:
    return _value_support().swap_out_within_tolerance(left, right, tolerance)


def _build_partial_metrics(liquidity, total_supply_value, virtual_initial_liquidity: bool):
    return PositionMetricsPartialResultBuilder().build(
        liquidity,
        total_supply_value,
        virtual_initial_liquidity,
    )


def _apply_data_quality_warnings(
    metrics: dict,
    *,
    pool_history_gap_summary: dict | None = None,
) -> dict:
    return PositionMetricsWarningApplier().apply(
        metrics,
        pool_history_gap_summary=pool_history_gap_summary,
    )


def _split_protocol_fee_redeemable_attos(
    *,
    redeemable_amount0: Decimal,
    redeemable_amount1: Decimal,
    live_liquidity: Decimal,
    history_liquidity: Decimal,
) -> tuple[int, int]:
    return _value_support().split_protocol_fee_redeemable_attos(
        redeemable_amount0=redeemable_amount0,
        redeemable_amount1=redeemable_amount1,
        live_liquidity=live_liquidity,
        history_liquidity=history_liquidity,
    )


def _history_liquidity(liquidity_history: list[dict]) -> Decimal:
    return _liquidity_history_support().history_liquidity(liquidity_history)


def _history_net_token_amounts(liquidity_history: list[dict]) -> tuple[Decimal, Decimal]:
    return _value_support().history_net_token_amounts(liquidity_history)


def _latest_position_liquidity_tx(liquidity_history: list[dict]) -> dict | None:
    return _liquidity_history_support().latest_position_liquidity_tx(liquidity_history)


def _build_observed_swap_fee_estimate(
    *,
    pool_transaction_history: list[dict] | None,
    latest_position_tx: dict | None,
    liquidity_basis: Decimal,
    total_supply_live: Decimal,
) -> tuple[Decimal, Decimal]:
    return _liquidity_history_support().build_observed_swap_fee_estimate(
        pool_transaction_history=pool_transaction_history,
        latest_position_tx=latest_position_tx,
        liquidity_basis=liquidity_basis,
        total_supply_live=total_supply_live,
    )


def _build_estimated_metrics_from_liquidity_history(
    partial_metrics: dict,
    *,
    liquidity_history: list[dict],
    pool_transaction_history: list[dict] | None,
    live_liquidity: Decimal | None,
    history_liquidity: Decimal,
) -> dict:
    return _liquidity_history_support().build_estimated_metrics_from_liquidity_history(
        partial_metrics,
        liquidity_history=liquidity_history,
        pool_transaction_history=pool_transaction_history,
        live_liquidity=live_liquidity,
        history_liquidity=history_liquidity,
    )


def _history_liquidity_before(
    liquidity_history: list[dict],
    latest_position_tx: dict,
) -> Decimal:
    return _liquidity_history_support().history_liquidity_before(liquidity_history, latest_position_tx)


def _liquidity_history_support() -> PositionMetricsLiquidityHistorySupport:
    return PositionMetricsLiquidityHistorySupport(
        analyzer_factory=lambda: PositionMetricsLiquidityHistoryAnalyzer(
            to_decimal=_to_decimal,
            to_attos=_to_attos,
            from_attos=_from_attos,
            normalize_non_negative=_normalize_non_negative,
            serialize_decimal=_serialize_decimal,
            split_protocol_fee_redeemable_attos=_split_protocol_fee_redeemable_attos,
            fee_numerator=SWAP_FEE_NUMERATOR,
            fee_denominator=SWAP_FEE_DENOMINATOR,
        ),
    )


def _swap_support() -> PositionMetricsSwapSupport:
    return PositionMetricsSwapSupport(
        default_support_factory=lambda: _build_swap_math_support(
            swap_fee_numerator=SWAP_FEE_NUMERATOR,
            swap_fee_denominator=SWAP_FEE_DENOMINATOR,
        ),
        support_factory=_build_swap_math_support,
    )


def _build_swap_math_support(
    *,
    swap_fee_numerator: int,
    swap_fee_denominator: int,
) -> PositionMetricsSwapMathSupport:
    return PositionMetricsSwapMathSupport(
        to_attos=_to_attos,
        from_attos=_from_attos,
        swap_fee_numerator=swap_fee_numerator,
        swap_fee_denominator=swap_fee_denominator,
        swap_out_tolerance_attos=SWAP_OUT_TOLERANCE_ATTOS,
    )


def _is_close(left: Decimal | None, right: Decimal | None, tolerance: Decimal = EPSILON) -> bool:
    return _value_support().is_close(left, right, tolerance)


def _normalize_non_negative(value: Decimal, tolerance: Decimal = EPSILON) -> Decimal:
    return _value_support().normalize_non_negative(value, tolerance)


def _value_support() -> PositionMetricsValueSupport:
    return PositionMetricsValueSupport(
        attos_scale=ATTOS_SCALE,
        display_quantum=DISPLAY_QUANTUM,
        epsilon=EPSILON,
        liquidity_mint_tolerance_attos=LIQUIDITY_MINT_TOLERANCE_ATTOS,
        swap_out_tolerance_attos=SWAP_OUT_TOLERANCE_ATTOS,
    )


def _mint_fee_attos(total_supply: int, reserve0: int, reserve1: int, k_last: int) -> int:
    return _swap_support().mint_fee_attos(total_supply, reserve0, reserve1, k_last)


def _sqrt_attos_product(amount0: int | None, amount1: int | None) -> int | None:
    return _swap_support().sqrt_attos_product(amount0, amount1)


def _swap_expected_out_attos(
    tx_type: str,
    reserve0: int,
    reserve1: int,
    amount0_in: int,
    amount1_in: int,
    *,
    fee_numerator: int = SWAP_FEE_NUMERATOR,
    fee_denominator: int = SWAP_FEE_DENOMINATOR,
) -> int | None:
    return _swap_support().swap_expected_out_attos(
        tx_type,
        reserve0,
        reserve1,
        amount0_in,
        amount1_in,
        fee_numerator=fee_numerator,
        fee_denominator=fee_denominator,
    )


def _apply_recorded_swap_attos(
    tx_type: str,
    reserve0: int,
    reserve1: int,
    *,
    amount0_in: int,
    amount0_out: int,
    amount1_in: int,
    amount1_out: int,
) -> tuple[int, int]:
    return _swap_support().apply_recorded_swap_attos(
        tx_type,
        reserve0,
        reserve1,
        amount0_in=amount0_in,
        amount0_out=amount0_out,
        amount1_in=amount1_in,
        amount1_out=amount1_out,
    )


def _infer_hidden_swap_before_batch(
    reserve0: int,
    reserve1: int,
    pool_transaction_history: list[dict],
    index: int,
) -> dict | None:
    return _swap_support().infer_hidden_swap_before_batch(reserve0, reserve1, pool_transaction_history, index)


def _reconstruct_pool_history(
    pool_transaction_history: list[dict],
    *,
    virtual_initial_liquidity: bool,
) -> tuple[list[dict] | None, list[dict] | None, list[str]]:
    return _replay_support().reconstruct_pool_history(
        pool_transaction_history,
        virtual_initial_liquidity=virtual_initial_liquidity,
    )


def _serialize_attos_debug(value: int | None) -> str | None:
    if value is None:
        return None
    return str(value)

def inspect_pool_history_replay(
    pool_transaction_history: list[dict],
    *,
    virtual_initial_liquidity: bool,
    swap_out_tolerance_attos: int = SWAP_OUT_TOLERANCE_ATTOS,
) -> dict:
    return _replay_support().inspect_pool_history_replay(
        pool_transaction_history,
        virtual_initial_liquidity=virtual_initial_liquidity,
        swap_out_tolerance_attos=swap_out_tolerance_attos,
    )


def _simulate_pool_history(
    pool_transaction_history: list[dict],
    *,
    virtual_initial_liquidity: bool,
) -> tuple[list[dict] | None, list[str]]:
    return _replay_support().simulate_pool_history(
        pool_transaction_history,
        virtual_initial_liquidity=virtual_initial_liquidity,
    )


def _effective_total_supply_attos_from_state(state: dict) -> int:
    return _replay_support().effective_total_supply_attos_from_state(state)


def _simulate_fee_free_from_open_state(states: list[dict], pool_transaction_history: list[dict], start_index: int) -> tuple[dict, list[str]]:
    return _replay_support().simulate_fee_free_from_open_state(
        states,
        pool_transaction_history,
        start_index,
    )


def _replay_support() -> PositionMetricsReplaySupport:
    return PositionMetricsReplaySupport(
        pool_history_reconstructor_factory=lambda: PositionMetricsPoolHistoryReconstructor(
            to_attos=_to_attos,
            swap_expected_out_attos=_swap_expected_out_attos,
            swap_out_within_tolerance=_swap_out_within_tolerance,
            infer_hidden_swap_before_batch=_infer_hidden_swap_before_batch,
            apply_recorded_swap_attos=_apply_recorded_swap_attos,
            sqrt_attos_product=_sqrt_attos_product,
            mint_fee_attos=_mint_fee_attos,
            attos_within_tolerance=_attos_within_tolerance,
        ),
        pool_history_replay_inspector_factory=lambda: PositionMetricsPoolHistoryReplayInspector(
            to_attos=_to_attos,
            swap_expected_out_attos=_swap_expected_out_attos,
            swap_out_within_tolerance=_swap_out_within_tolerance,
            infer_hidden_swap_before_batch=_infer_hidden_swap_before_batch,
            apply_recorded_swap_attos=_apply_recorded_swap_attos,
            sqrt_attos_product=_sqrt_attos_product,
            mint_fee_attos=_mint_fee_attos,
            attos_within_tolerance=_attos_within_tolerance,
            serialize_attos_debug=_serialize_attos_debug,
        ),
        fee_free_open_state_simulator_factory=lambda: PositionMetricsFeeFreeOpenStateSimulator(
            to_attos=_to_attos,
        ),
        mint_fee_attos=_mint_fee_attos,
    )


def _try_enrich_metrics_with_swap_history(
    partial_metrics: dict,
    *,
    liquidity_history: list[dict],
    pool_transaction_history: list[dict] | None,
    owner_is_fee_to: bool,
) -> tuple[dict | None, list[str]]:
    return PositionMetricsSwapHistoryExactnessSolver(
        to_decimal=_to_decimal,
        history_liquidity=_history_liquidity,
        reconstruct_pool_history=_reconstruct_pool_history,
        history_liquidity_before=_history_liquidity_before,
        split_protocol_fee_redeemable_attos=_split_protocol_fee_redeemable_attos,
        from_attos=_from_attos,
        effective_total_supply_attos_from_state=_effective_total_supply_attos_from_state,
        attos_within_tolerance=_attos_within_tolerance,
        simulate_fee_free_from_open_state=_simulate_fee_free_from_open_state,
        normalize_non_negative=_normalize_non_negative,
        serialize_decimal=_serialize_decimal,
        to_attos=_to_attos,
        epsilon=EPSILON,
    ).solve(
        partial_metrics,
        liquidity_history=liquidity_history,
        pool_transaction_history=pool_transaction_history,
        owner_is_fee_to=owner_is_fee_to,
    )


def _enrich_metrics_with_history(
    partial_metrics: dict,
    *,
    liquidity_history: list[dict] | None,
    pool_transaction_history: list[dict] | None,
    pool_swap_count_since_open: int | None,
    owner_is_fee_to: bool,
):
    return PositionMetricsHistoryEnricher(
        to_decimal=_to_decimal,
        history_liquidity=_history_liquidity,
        try_enrich_metrics_with_swap_history=_try_enrich_metrics_with_swap_history,
        serialize_decimal=_serialize_decimal,
        build_estimated_metrics_from_liquidity_history=_build_estimated_metrics_from_liquidity_history,
    ).enrich(
        partial_metrics,
        liquidity_history=liquidity_history,
        pool_transaction_history=pool_transaction_history,
        pool_swap_count_since_open=pool_swap_count_since_open,
        owner_is_fee_to=owner_is_fee_to,
    )


def _payload_enricher() -> PositionMetricsPayloadEnricher:
    return PositionMetricsPayloadEnricher(
        live_history_reconciler=PositionMetricsLiveHistoryReconciler(
            normalize_live_transaction=_normalize_live_transaction,
            merge_transaction_history=_merge_transaction_history,
            build_transaction_gap_summary=_build_transaction_gap_summary,
        ),
        build_partial_metrics=_build_partial_metrics,
        enrich_metrics_with_history=_enrich_metrics_with_history,
        apply_data_quality_warnings=_apply_data_quality_warnings,
        account_payload_to_string=_account_payload_to_string,
    )


def _facade_support() -> PositionMetricsFacadeSupport:
    from integration.pool_application_client import PoolApplicationClient

    return PositionMetricsFacadeSupport(
        parse_account=parse_account,
        running_in_k8s=running_in_k8s,
        pool_application_client_factory=PoolApplicationClient,
        payload_enricher_factory=_payload_enricher,
    )


async def fetch_live_position_metrics(
    position: dict,
    swap_base_url: str,
    *,
    liquidity_history: list[dict] | None = None,
    pool_transaction_history: list[dict] | None = None,
    pool_swap_count_since_open: int | None = None,
    pool_history_gap_summary: dict | None = None,
    post=async_request.post,
    in_k8s: bool | None = None,
):
    return await _facade_support().fetch_live_position_metrics(
        position,
        swap_base_url,
        liquidity_history=liquidity_history,
        pool_transaction_history=pool_transaction_history,
        pool_swap_count_since_open=pool_swap_count_since_open,
        pool_history_gap_summary=pool_history_gap_summary,
        post=post,
        in_k8s=in_k8s,
    )


def enrich_position_metrics_from_payload(
    position: dict,
    payload: dict,
    *,
    liquidity_history: list[dict] | None = None,
    pool_transaction_history: list[dict] | None = None,
    pool_swap_count_since_open: int | None = None,
    pool_history_gap_summary: dict | None = None,
    position_basis_snapshot: dict | None = None,
    pool_state_snapshot: dict | None = None,
):
    return _facade_support().enrich_position_metrics_from_payload(
        position,
        payload,
        liquidity_history=liquidity_history,
        pool_transaction_history=pool_transaction_history,
        pool_swap_count_since_open=pool_swap_count_since_open,
        pool_history_gap_summary=pool_history_gap_summary,
        position_basis_snapshot=position_basis_snapshot,
        pool_state_snapshot=pool_state_snapshot,
    )
