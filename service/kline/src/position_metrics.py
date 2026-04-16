import async_request
from environment import running_in_k8s
from decimal import Decimal
import math

EPSILON = Decimal('0.000000000001')
DISPLAY_QUANTUM = Decimal('0.000000000000000001')
ATTOS_SCALE = 10 ** 18
LIQUIDITY_MINT_TOLERANCE_ATTOS = 100
SWAP_OUT_TOLERANCE_ATTOS = 1
SWAP_FEE_NUMERATOR = 997
SWAP_FEE_DENOMINATOR = 1000


def parse_account(account: str):
    chain_id, owner = account.split(':', 1)
    return {
        'chain_id': chain_id,
        'owner': owner,
    }


def pool_application_url(base_url: str, pool_application: str, in_k8s: bool | None = None):
    chain_id, application_id = pool_application.split(':', 1)
    prefix = '' if (running_in_k8s() if in_k8s is None else in_k8s) else '/query'
    short_application_id = application_id[2:] if application_id.startswith('0x') else application_id
    return f'{base_url}{prefix}/chains/{chain_id}/applications/{short_application_id}'


def build_position_metrics_query(owner: dict):
    return {
        'query': '''
            query PositionMetrics($owner: Account!) {
              pool
              totalSupply
              virtualInitialLiquidity
              liquidity(owner: $owner) {
                liquidity
                amount0
                amount1
              }
              latestTransactions(startId: 0)
            }
        ''',
        'variables': {
            'owner': owner,
        },
    }


def build_position_metrics_legacy_query(owner: dict):
    return {
        'query': '''
            query PositionMetricsLegacy($owner: Account!) {
              pool
              virtualInitialLiquidity
              liquidity(owner: $owner) {
                liquidity
                amount0
                amount1
              }
              latestTransactions(startId: 0)
            }
        ''',
        'variables': {
            'owner': owner,
        },
    }


def _graphql_unknown_field(payload: dict, field_name: str) -> bool:
    for error in payload.get('errors') or []:
        message = str(error.get('message') or '')
        if f'Unknown field "{field_name}"' in message:
            return True
    return False


def _to_decimal(value):
    if value is None:
        return None
    return Decimal(str(value))


def _serialize_decimal(value: Decimal | None):
    if value is None:
        return None
    if value == 0:
        return '0'
    return format(value.quantize(DISPLAY_QUANTUM).normalize(), 'f')


def _account_payload_to_string(account: dict | None) -> str | None:
    if not isinstance(account, dict):
        return None
    chain_id = account.get('chain_id')
    owner = account.get('owner')
    if chain_id is None or owner is None:
        return None
    return f'{chain_id}:{owner}'


def _normalize_live_transaction(tx: dict) -> dict:
    return {
        'transaction_id': tx.get('transactionId'),
        'transaction_type': tx.get('transactionType'),
        'from_account': _account_payload_to_string(tx.get('from')),
        'amount_0_in': tx.get('amount0In'),
        'amount_0_out': tx.get('amount0Out'),
        'amount_1_in': tx.get('amount1In'),
        'amount_1_out': tx.get('amount1Out'),
        'liquidity': tx.get('liquidity'),
        # Chain service uses microseconds; keep one consistent unit within live history.
        'created_at': int(tx.get('createdAt') or 0),
    }


def _history_transaction_identity(tx: dict) -> tuple:
    return (
        int(tx.get('transaction_id') or 0),
        int(tx.get('created_at') or 0),
        tx.get('transaction_type'),
        tx.get('from_account'),
    )


def _merge_transaction_history(
    persisted_history: list[dict] | None,
    live_history: list[dict] | None,
) -> list[dict]:
    merged: dict[tuple, dict] = {}

    for tx in persisted_history or []:
        merged[_history_transaction_identity(tx)] = tx

    for tx in live_history or []:
        merged[_history_transaction_identity(tx)] = tx

    return sorted(
        merged.values(),
        key=lambda row: (
            int(row.get('created_at') or 0),
            int(row.get('transaction_id') or 0),
        ),
    )


def _build_transaction_gap_summary(
    transaction_history: list[dict] | None,
    *,
    start_id: int | None = None,
    end_id: int | None = None,
    sample_limit: int = 8,
) -> dict:
    transaction_ids = sorted(
        {
            int(tx.get('transaction_id'))
            for tx in (transaction_history or [])
            if tx.get('transaction_id') is not None
        }
    )
    if not transaction_ids:
        return {
            'has_internal_gaps': False,
            'start_id': None,
            'end_id': None,
            'missing_count': 0,
            'missing_ids_sample': [],
        }

    lower_bound = transaction_ids[0] if start_id is None else max(int(start_id), transaction_ids[0])
    upper_bound = transaction_ids[-1] if end_id is None else min(int(end_id), transaction_ids[-1])
    if lower_bound > upper_bound:
        return {
            'has_internal_gaps': False,
            'start_id': lower_bound,
            'end_id': upper_bound,
            'missing_count': 0,
            'missing_ids_sample': [],
        }

    observed_set = set(transaction_ids)
    missing_ids_sample = []
    missing_count = 0
    for transaction_id in range(lower_bound, upper_bound + 1):
        if transaction_id in observed_set:
            continue
        missing_count += 1
        if len(missing_ids_sample) < int(sample_limit):
            missing_ids_sample.append(transaction_id)

    return {
        'has_internal_gaps': missing_count > 0,
        'start_id': lower_bound,
        'end_id': upper_bound,
        'missing_count': missing_count,
        'missing_ids_sample': missing_ids_sample,
    }


def _to_attos(value) -> int | None:
    if value is None:
        return None
    return int((Decimal(str(value)) * ATTOS_SCALE).to_integral_value())


def _from_attos(value: int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value) / Decimal(ATTOS_SCALE)


def _attos_within_tolerance(left: int, right: int, tolerance: int = LIQUIDITY_MINT_TOLERANCE_ATTOS) -> bool:
    return abs(left - right) <= tolerance


def _swap_out_within_tolerance(left: int, right: int, tolerance: int = SWAP_OUT_TOLERANCE_ATTOS) -> bool:
    return abs(left - right) <= tolerance


def _build_partial_metrics(liquidity, total_supply_value, virtual_initial_liquidity: bool):
    return {
        'position_liquidity_live': liquidity.get('liquidity'),
        'total_supply_live': total_supply_value,
        'exact_share_ratio': None,
        'redeemable_amount0': liquidity.get('amount0'),
        'redeemable_amount1': liquidity.get('amount1'),
        'virtual_initial_liquidity': virtual_initial_liquidity,
        'metrics_status': 'partial_live_redeemable_only',
        'exact_fee_supported': False,
        'exact_principal_supported': False,
        'owner_is_fee_to': False,
        'computation_blockers': [],
        'principal_amount0': None,
        'principal_amount1': None,
        'fee_amount0': '0',
        'fee_amount1': '0',
        'protocol_fee_amount0': '0',
        'protocol_fee_amount1': '0',
        'value_warning_codes': [],
        'value_warning_message': None,
    }


def _apply_data_quality_warnings(
    metrics: dict,
    *,
    pool_history_gap_summary: dict | None = None,
) -> dict:
    warning_codes = list(metrics.get('value_warning_codes') or [])
    warning_message = metrics.get('value_warning_message')
    blockers = list(metrics.get('computation_blockers') or [])

    if pool_history_gap_summary and bool(pool_history_gap_summary.get('has_internal_gaps')):
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


def _split_protocol_fee_redeemable_attos(
    *,
    redeemable_amount0: Decimal,
    redeemable_amount1: Decimal,
    live_liquidity: Decimal,
    history_liquidity: Decimal,
) -> tuple[int, int]:
    redeemable_amount0_attos = _to_attos(redeemable_amount0) or 0
    redeemable_amount1_attos = _to_attos(redeemable_amount1) or 0
    live_liquidity_attos = _to_attos(live_liquidity) or 0
    history_liquidity_attos = _to_attos(history_liquidity) or 0
    protocol_fee_liquidity_attos = max(live_liquidity_attos - history_liquidity_attos, 0)

    if protocol_fee_liquidity_attos == 0 or live_liquidity_attos == 0:
        return 0, 0

    return (
        redeemable_amount0_attos * protocol_fee_liquidity_attos // live_liquidity_attos,
        redeemable_amount1_attos * protocol_fee_liquidity_attos // live_liquidity_attos,
    )


def _history_liquidity(liquidity_history: list[dict]) -> Decimal:
    current_liquidity = Decimal('0')
    for row in liquidity_history:
        liquidity = _to_decimal(row.get('liquidity')) or Decimal('0')
        if row.get('transaction_type') == 'AddLiquidity':
            current_liquidity += liquidity
        elif row.get('transaction_type') == 'RemoveLiquidity':
            current_liquidity -= liquidity
    return current_liquidity


def _history_net_token_amounts(liquidity_history: list[dict]) -> tuple[Decimal, Decimal]:
    amount0 = Decimal('0')
    amount1 = Decimal('0')
    for row in liquidity_history:
        liquidity = _to_decimal(row.get('liquidity')) or Decimal('0')
        # Ignore bootstrap-style rows that moved tokens but never minted
        # redeemable LP shares for this owner; they should not inflate
        # the estimated principal basis.
        if liquidity <= Decimal('0'):
            continue
        if row.get('transaction_type') == 'AddLiquidity':
            amount0 += _to_decimal(row.get('amount_0_in')) or Decimal('0')
            amount1 += _to_decimal(row.get('amount_1_in')) or Decimal('0')
        elif row.get('transaction_type') == 'RemoveLiquidity':
            amount0 -= _to_decimal(row.get('amount_0_out')) or Decimal('0')
            amount1 -= _to_decimal(row.get('amount_1_out')) or Decimal('0')
    return amount0, amount1


def _latest_position_liquidity_tx(liquidity_history: list[dict]) -> dict | None:
    if not liquidity_history:
        return None
    return max(
        liquidity_history,
        key=lambda row: (
            int(row.get('created_at') or 0),
            int(row.get('transaction_id') or 0),
        ),
    )


def _build_observed_swap_fee_estimate(
    *,
    pool_transaction_history: list[dict] | None,
    latest_position_tx: dict | None,
    liquidity_basis: Decimal,
    total_supply_live: Decimal,
) -> tuple[Decimal, Decimal]:
    if not pool_transaction_history or latest_position_tx is None:
        return Decimal('0'), Decimal('0')
    if liquidity_basis <= Decimal('0') or total_supply_live <= Decimal('0'):
        return Decimal('0'), Decimal('0')

    latest_created_at = int(latest_position_tx.get('created_at') or 0)
    latest_transaction_id = int(latest_position_tx.get('transaction_id') or 0)
    share_ratio = liquidity_basis / total_supply_live
    fee_rate = Decimal(SWAP_FEE_DENOMINATOR - SWAP_FEE_NUMERATOR) / Decimal(SWAP_FEE_DENOMINATOR)

    observed_fee0 = Decimal('0')
    observed_fee1 = Decimal('0')
    for tx in pool_transaction_history:
        tx_key = (
            int(tx.get('created_at') or 0),
            int(tx.get('transaction_id') or 0),
        )
        if tx_key < (latest_created_at, latest_transaction_id):
            continue

        tx_type = tx.get('transaction_type')
        if tx_type == 'SellToken0':
            amount0_in = _to_decimal(tx.get('amount_0_in')) or Decimal('0')
            if amount0_in > Decimal('0'):
                observed_fee0 += amount0_in * fee_rate * share_ratio
        elif tx_type == 'BuyToken0':
            amount1_in = _to_decimal(tx.get('amount_1_in')) or Decimal('0')
            if amount1_in > Decimal('0'):
                observed_fee1 += amount1_in * fee_rate * share_ratio

    return observed_fee0, observed_fee1


def _build_estimated_metrics_from_liquidity_history(
    partial_metrics: dict,
    *,
    liquidity_history: list[dict],
    pool_transaction_history: list[dict] | None,
    live_liquidity: Decimal | None,
    history_liquidity: Decimal,
) -> dict:
    redeemable_amount0 = _to_decimal(partial_metrics['redeemable_amount0'])
    redeemable_amount1 = _to_decimal(partial_metrics['redeemable_amount1'])
    if redeemable_amount0 is None or redeemable_amount1 is None:
        return partial_metrics
    has_token_amount_history = any(
        row.get('amount_0_in') is not None
        or row.get('amount_0_out') is not None
        or row.get('amount_1_in') is not None
        or row.get('amount_1_out') is not None
        for row in liquidity_history
    )
    if not has_token_amount_history:
        return partial_metrics

    protocol_fee_amount0 = Decimal('0')
    protocol_fee_amount1 = Decimal('0')
    if live_liquidity is not None and live_liquidity > history_liquidity > Decimal('0'):
        protocol_fee_amount0_attos, protocol_fee_amount1_attos = _split_protocol_fee_redeemable_attos(
            redeemable_amount0=redeemable_amount0,
            redeemable_amount1=redeemable_amount1,
            live_liquidity=live_liquidity,
            history_liquidity=history_liquidity,
        )
        protocol_fee_amount0 = _from_attos(protocol_fee_amount0_attos) or Decimal('0')
        protocol_fee_amount1 = _from_attos(protocol_fee_amount1_attos) or Decimal('0')

    redeemable_ex_protocol0 = _normalize_non_negative(redeemable_amount0 - protocol_fee_amount0)
    redeemable_ex_protocol1 = _normalize_non_negative(redeemable_amount1 - protocol_fee_amount1)
    total_supply_live = _to_decimal(partial_metrics.get('total_supply_live')) or Decimal('0')
    latest_position_tx = _latest_position_liquidity_tx(liquidity_history)
    liquidity_basis = min(history_liquidity, live_liquidity or history_liquidity)
    observed_fee0, observed_fee1 = _build_observed_swap_fee_estimate(
        pool_transaction_history=pool_transaction_history,
        latest_position_tx=latest_position_tx,
        liquidity_basis=liquidity_basis,
        total_supply_live=total_supply_live,
    )
    fee_amount0 = min(redeemable_ex_protocol0, _normalize_non_negative(observed_fee0))
    fee_amount1 = min(redeemable_ex_protocol1, _normalize_non_negative(observed_fee1))
    principal_amount0 = _normalize_non_negative(redeemable_ex_protocol0 - fee_amount0)
    principal_amount1 = _normalize_non_negative(redeemable_ex_protocol1 - fee_amount1)

    partial_metrics['metrics_status'] = 'estimated_live_redeemable_with_history'
    partial_metrics['principal_amount0'] = _serialize_decimal(principal_amount0)
    partial_metrics['principal_amount1'] = _serialize_decimal(principal_amount1)
    partial_metrics['fee_amount0'] = _serialize_decimal(fee_amount0)
    partial_metrics['fee_amount1'] = _serialize_decimal(fee_amount1)
    partial_metrics['protocol_fee_amount0'] = _serialize_decimal(protocol_fee_amount0)
    partial_metrics['protocol_fee_amount1'] = _serialize_decimal(protocol_fee_amount1)
    return partial_metrics


def _history_liquidity_before(
    liquidity_history: list[dict],
    latest_position_tx: dict,
) -> Decimal:
    current_liquidity = Decimal('0')
    latest_created_at = int(latest_position_tx.get('created_at') or 0)
    latest_transaction_id = int(latest_position_tx.get('transaction_id') or 0)

    for row in liquidity_history:
        row_created_at = int(row.get('created_at') or 0)
        row_transaction_id = int(row.get('transaction_id') or 0)
        if (row_created_at, row_transaction_id) >= (latest_created_at, latest_transaction_id):
            break

        liquidity = _to_decimal(row.get('liquidity')) or Decimal('0')
        if row.get('transaction_type') == 'AddLiquidity':
            current_liquidity += liquidity
        elif row.get('transaction_type') == 'RemoveLiquidity':
            current_liquidity -= liquidity

    return current_liquidity


def _is_close(left: Decimal | None, right: Decimal | None, tolerance: Decimal = EPSILON) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) <= tolerance


def _normalize_non_negative(value: Decimal, tolerance: Decimal = EPSILON) -> Decimal:
    if abs(value) <= tolerance:
        return Decimal('0')
    return value


def _mint_fee_attos(total_supply: int, reserve0: int, reserve1: int, k_last: int) -> int:
    if k_last == 0:
        return 0
    root_k = math.isqrt(reserve0 * reserve1)
    if root_k <= k_last:
        return 0
    denominator = root_k * 5 + k_last
    if denominator == 0:
        return 0
    return total_supply * (root_k - k_last) // denominator


def _sqrt_attos_product(amount0: int | None, amount1: int | None) -> int | None:
    if amount0 is None or amount1 is None:
        return None
    if amount0 < 0 or amount1 < 0:
        return None
    return math.isqrt(amount0 * amount1)


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
    if reserve0 <= 0 or reserve1 <= 0:
        return None
    if tx_type == 'BuyToken0':
        if amount1_in <= 0:
            return None
        amount_in_with_fee = amount1_in * fee_numerator
        denominator = reserve1 * fee_denominator + amount_in_with_fee
        if denominator <= 0:
            return None
        return amount_in_with_fee * reserve0 // denominator
    if tx_type == 'SellToken0':
        if amount0_in <= 0:
            return None
        amount_in_with_fee = amount0_in * fee_numerator
        denominator = reserve0 * fee_denominator + amount_in_with_fee
        if denominator <= 0:
            return None
        return amount_in_with_fee * reserve1 // denominator
    return None


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
    if tx_type == 'BuyToken0':
        return reserve0 - amount0_out, reserve1 + amount1_in
    return reserve0 + amount0_in, reserve1 - amount1_out


def _decimal_sign(value: Decimal) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _solve_hidden_buy_before_swap(
    reserve0: int,
    reserve1: int,
    tx: dict,
) -> dict | None:
    recorded_amount0_out = _to_attos(tx.get('amount_0_out')) or 0
    recorded_amount1_out = _to_attos(tx.get('amount_1_out')) or 0
    amount0_in = _to_attos(tx.get('amount_0_in')) or 0
    amount1_in = _to_attos(tx.get('amount_1_in')) or 0

    if tx.get('transaction_type') == 'BuyToken0':
        target_out = recorded_amount0_out
    elif tx.get('transaction_type') == 'SellToken0':
        target_out = recorded_amount1_out
    else:
        return None
    if target_out <= 0:
        return None

    reserve0_d = Decimal(reserve0)
    reserve1_d = Decimal(reserve1)
    target_out_d = Decimal(target_out)
    amount0_in_d = Decimal(amount0_in)
    amount1_in_d = Decimal(amount1_in)

    def hidden_buy_out(x: Decimal) -> Decimal:
        amount_in_with_fee = x * SWAP_FEE_NUMERATOR
        denominator = reserve1_d * SWAP_FEE_DENOMINATOR + amount_in_with_fee
        if denominator <= 0:
            return Decimal('0')
        return amount_in_with_fee * reserve0_d / denominator

    def replay_error(x: Decimal) -> Decimal:
        hidden_amount0_out = hidden_buy_out(x)
        adjusted_reserve0 = reserve0_d - hidden_amount0_out
        adjusted_reserve1 = reserve1_d + x
        if adjusted_reserve0 <= 0 or adjusted_reserve1 <= 0:
            return Decimal('0') - target_out_d
        if tx.get('transaction_type') == 'BuyToken0':
            amount_in_with_fee = amount1_in_d * SWAP_FEE_NUMERATOR
            denominator = adjusted_reserve1 * SWAP_FEE_DENOMINATOR + amount_in_with_fee
            expected = amount_in_with_fee * adjusted_reserve0 / denominator
        else:
            amount_in_with_fee = amount0_in_d * SWAP_FEE_NUMERATOR
            denominator = adjusted_reserve0 * SWAP_FEE_DENOMINATOR + amount_in_with_fee
            expected = amount_in_with_fee * adjusted_reserve1 / denominator
        return expected - target_out_d

    low = Decimal('1')
    high = max(Decimal(reserve1), Decimal(amount1_in or amount0_in or 1))
    low_sign = _decimal_sign(replay_error(low))
    high_sign = _decimal_sign(replay_error(high))
    while high_sign != 0 and high_sign == low_sign and high < Decimal(reserve1 * 1024):
        high *= 2
        high_sign = _decimal_sign(replay_error(high))
    if low_sign != 0 and high_sign != 0 and high_sign == low_sign:
        return None

    for _ in range(256):
        mid = (low + high) / 2
        mid_sign = _decimal_sign(replay_error(mid))
        if mid_sign == 0:
            low = high = mid
            break
        if low_sign == 0 or mid_sign == low_sign:
            low = mid
            low_sign = mid_sign
        else:
            high = mid
            high_sign = mid_sign

    hidden_amount1_in = int(high.to_integral_value())
    if hidden_amount1_in <= 0:
        return None
    hidden_amount0_out = _swap_expected_out_attos(
        'BuyToken0',
        reserve0,
        reserve1,
        0,
        hidden_amount1_in,
    )
    if hidden_amount0_out is None or hidden_amount0_out <= 0 or hidden_amount0_out >= reserve0:
        return None
    return {
        'transaction_id': None,
        'transaction_type': 'BuyToken0',
        'from_account': None,
        'amount_0_in': None,
        'amount_0_out': _from_attos(hidden_amount0_out),
        'amount_1_in': _from_attos(hidden_amount1_in),
        'amount_1_out': None,
        'liquidity': None,
        'created_at': tx.get('created_at'),
        'synthetic_hidden_swap': True,
    }


def _solve_hidden_sell_before_swap(
    reserve0: int,
    reserve1: int,
    tx: dict,
) -> dict | None:
    recorded_amount0_out = _to_attos(tx.get('amount_0_out')) or 0
    recorded_amount1_out = _to_attos(tx.get('amount_1_out')) or 0
    amount0_in = _to_attos(tx.get('amount_0_in')) or 0
    amount1_in = _to_attos(tx.get('amount_1_in')) or 0

    if tx.get('transaction_type') == 'BuyToken0':
        target_out = recorded_amount0_out
    elif tx.get('transaction_type') == 'SellToken0':
        target_out = recorded_amount1_out
    else:
        return None
    if target_out <= 0:
        return None

    reserve0_d = Decimal(reserve0)
    reserve1_d = Decimal(reserve1)
    target_out_d = Decimal(target_out)
    amount0_in_d = Decimal(amount0_in)
    amount1_in_d = Decimal(amount1_in)

    def hidden_sell_out(x: Decimal) -> Decimal:
        amount_in_with_fee = x * SWAP_FEE_NUMERATOR
        denominator = reserve0_d * SWAP_FEE_DENOMINATOR + amount_in_with_fee
        if denominator <= 0:
            return Decimal('0')
        return amount_in_with_fee * reserve1_d / denominator

    def replay_error(x: Decimal) -> Decimal:
        hidden_amount1_out = hidden_sell_out(x)
        adjusted_reserve0 = reserve0_d + x
        adjusted_reserve1 = reserve1_d - hidden_amount1_out
        if adjusted_reserve0 <= 0 or adjusted_reserve1 <= 0:
            return Decimal('0') - target_out_d
        if tx.get('transaction_type') == 'BuyToken0':
            amount_in_with_fee = amount1_in_d * SWAP_FEE_NUMERATOR
            denominator = adjusted_reserve1 * SWAP_FEE_DENOMINATOR + amount_in_with_fee
            expected = amount_in_with_fee * adjusted_reserve0 / denominator
        else:
            amount_in_with_fee = amount0_in_d * SWAP_FEE_NUMERATOR
            denominator = adjusted_reserve0 * SWAP_FEE_DENOMINATOR + amount_in_with_fee
            expected = amount_in_with_fee * adjusted_reserve1 / denominator
        return expected - target_out_d

    low = Decimal('1')
    high = max(Decimal(reserve0), Decimal(amount0_in or amount1_in or 1))
    low_sign = _decimal_sign(replay_error(low))
    high_sign = _decimal_sign(replay_error(high))
    while high_sign != 0 and high_sign == low_sign and high < Decimal(reserve0 * 1024):
        high *= 2
        high_sign = _decimal_sign(replay_error(high))
    if low_sign != 0 and high_sign != 0 and high_sign == low_sign:
        return None

    for _ in range(256):
        mid = (low + high) / 2
        mid_sign = _decimal_sign(replay_error(mid))
        if mid_sign == 0:
            low = high = mid
            break
        if low_sign == 0 or mid_sign == low_sign:
            low = mid
            low_sign = mid_sign
        else:
            high = mid
            high_sign = mid_sign

    hidden_amount0_in = int(high.to_integral_value())
    if hidden_amount0_in <= 0:
        return None
    hidden_amount1_out = _swap_expected_out_attos(
        'SellToken0',
        reserve0,
        reserve1,
        hidden_amount0_in,
        0,
    )
    if hidden_amount1_out is None or hidden_amount1_out <= 0 or hidden_amount1_out >= reserve1:
        return None
    return {
        'transaction_id': None,
        'transaction_type': 'SellToken0',
        'from_account': None,
        'amount_0_in': _from_attos(hidden_amount0_in),
        'amount_0_out': None,
        'amount_1_in': None,
        'amount_1_out': _from_attos(hidden_amount1_out),
        'liquidity': None,
        'created_at': tx.get('created_at'),
        'synthetic_hidden_swap': True,
    }


def _infer_hidden_swap_before_batch(
    reserve0: int,
    reserve1: int,
    pool_transaction_history: list[dict],
    index: int,
) -> dict | None:
    tx = pool_transaction_history[index]
    next_tx = pool_transaction_history[index + 1] if index + 1 < len(pool_transaction_history) else None
    if next_tx is None:
        return None
    if int(next_tx.get('created_at') or 0) != int(tx.get('created_at') or 0):
        return None
    if next_tx.get('transaction_type') not in {'BuyToken0', 'SellToken0'}:
        return None

    for candidate in (
        _solve_hidden_buy_before_swap(reserve0, reserve1, tx),
        _solve_hidden_sell_before_swap(reserve0, reserve1, tx),
    ):
        if candidate is None:
            continue

        current_reserve0, current_reserve1 = _apply_recorded_swap_attos(
            candidate['transaction_type'],
            reserve0,
            reserve1,
            amount0_in=_to_attos(candidate.get('amount_0_in')) or 0,
            amount0_out=_to_attos(candidate.get('amount_0_out')) or 0,
            amount1_in=_to_attos(candidate.get('amount_1_in')) or 0,
            amount1_out=_to_attos(candidate.get('amount_1_out')) or 0,
        )

        for replay_tx in (tx, next_tx):
            expected_out = _swap_expected_out_attos(
                replay_tx.get('transaction_type'),
                current_reserve0,
                current_reserve1,
                _to_attos(replay_tx.get('amount_0_in')) or 0,
                _to_attos(replay_tx.get('amount_1_in')) or 0,
            )
            recorded_out = (
                _to_attos(replay_tx.get('amount_0_out')) or 0
                if replay_tx.get('transaction_type') == 'BuyToken0'
                else _to_attos(replay_tx.get('amount_1_out')) or 0
            )
            if expected_out is None or not _swap_out_within_tolerance(expected_out, recorded_out):
                break
            current_reserve0, current_reserve1 = _apply_recorded_swap_attos(
                replay_tx.get('transaction_type'),
                current_reserve0,
                current_reserve1,
                amount0_in=_to_attos(replay_tx.get('amount_0_in')) or 0,
                amount0_out=_to_attos(replay_tx.get('amount_0_out')) or 0,
                amount1_in=_to_attos(replay_tx.get('amount_1_in')) or 0,
                amount1_out=_to_attos(replay_tx.get('amount_1_out')) or 0,
            )
        else:
            return candidate

    return None


def _reconstruct_pool_history(
    pool_transaction_history: list[dict],
    *,
    virtual_initial_liquidity: bool,
) -> tuple[list[dict] | None, list[dict] | None, list[str]]:
    if not pool_transaction_history:
        return None, None, ['missing_pool_transaction_history']

    reserve0 = 0
    reserve1 = 0
    total_supply = 0
    k_last = 0
    states = []
    effective_history = []
    blockers = []
    index = 0

    while index < len(pool_transaction_history):
        tx = pool_transaction_history[index]
        tx_type = tx.get('transaction_type')
        amount0_in = _to_attos(tx.get('amount_0_in')) or 0
        amount0_out = _to_attos(tx.get('amount_0_out')) or 0
        amount1_in = _to_attos(tx.get('amount_1_in')) or 0
        amount1_out = _to_attos(tx.get('amount_1_out')) or 0
        liquidity = _to_attos(tx.get('liquidity')) or 0

        if tx_type in {'BuyToken0', 'SellToken0'}:
            expected_out = _swap_expected_out_attos(
                tx_type,
                reserve0,
                reserve1,
                amount0_in,
                amount1_in,
            )
            recorded_out = amount0_out if tx_type == 'BuyToken0' else amount1_out
            if expected_out is None or not _swap_out_within_tolerance(expected_out, recorded_out):
                hidden_swap = _infer_hidden_swap_before_batch(
                    reserve0,
                    reserve1,
                    pool_transaction_history,
                    index,
                )
                if hidden_swap is None:
                    blockers.append('pool_history_contains_invalid_swap_amounts')
                    break
                hidden_type = hidden_swap.get('transaction_type')
                reserve0, reserve1 = _apply_recorded_swap_attos(
                    hidden_type,
                    reserve0,
                    reserve1,
                    amount0_in=_to_attos(hidden_swap.get('amount_0_in')) or 0,
                    amount0_out=_to_attos(hidden_swap.get('amount_0_out')) or 0,
                    amount1_in=_to_attos(hidden_swap.get('amount_1_in')) or 0,
                    amount1_out=_to_attos(hidden_swap.get('amount_1_out')) or 0,
                )
                effective_history.append(hidden_swap)
                states.append({
                    'transaction_id': hidden_swap.get('transaction_id'),
                    'created_at': hidden_swap.get('created_at'),
                    'transaction_type': hidden_type,
                    'from_account': hidden_swap.get('from_account'),
                    'reserve0_after': reserve0,
                    'reserve1_after': reserve1,
                    'total_supply_after': total_supply,
                    'k_last_after': k_last,
                })
                expected_out = _swap_expected_out_attos(
                    tx_type,
                    reserve0,
                    reserve1,
                    amount0_in,
                    amount1_in,
                )
                if expected_out is None or not _swap_out_within_tolerance(expected_out, recorded_out):
                    blockers.append('pool_history_contains_invalid_swap_amounts')
                    break

        if tx_type == 'AddLiquidity':
            if reserve0 == 0 and reserve1 == 0:
                expected_liquidity = _sqrt_attos_product(amount0_in, amount1_in)
                if expected_liquidity is None:
                    blockers.append('pool_history_bootstrap_supply_unknown')
                    break
                if virtual_initial_liquidity:
                    if liquidity != 0:
                        blockers.append('pool_history_bootstrap_supply_unknown')
                        break
                    total_supply = expected_liquidity
                else:
                    if liquidity != expected_liquidity:
                        blockers.append('pool_history_bootstrap_supply_unknown')
                        break
                    total_supply = liquidity
                reserve0 += amount0_in
                reserve1 += amount1_in
                k_last = _sqrt_attos_product(reserve0, reserve1) or 0
            else:
                fee_share = _mint_fee_attos(total_supply, reserve0, reserve1, k_last)
                total_supply += fee_share
                expected_liquidity = min(
                    amount0_in * total_supply // reserve0,
                    amount1_in * total_supply // reserve1,
                )
                if not _attos_within_tolerance(liquidity, expected_liquidity):
                    blockers.append('pool_history_liquidity_mint_mismatch')
                    break
                total_supply += liquidity
                reserve0 += amount0_in
                reserve1 += amount1_in
                k_last = _sqrt_attos_product(reserve0, reserve1) or 0
        elif tx_type == 'RemoveLiquidity':
            fee_share = _mint_fee_attos(total_supply, reserve0, reserve1, k_last)
            total_supply += fee_share
            if liquidity > total_supply or amount0_out > reserve0 or amount1_out > reserve1:
                blockers.append('pool_history_remove_liquidity_invalid')
                break
            total_supply -= liquidity
            reserve0 -= amount0_out
            reserve1 -= amount1_out
            k_last = _sqrt_attos_product(reserve0, reserve1) or 0
        elif tx_type in {'BuyToken0', 'SellToken0'}:
            reserve0, reserve1 = _apply_recorded_swap_attos(
                tx_type,
                reserve0,
                reserve1,
                amount0_in=amount0_in,
                amount0_out=amount0_out,
                amount1_in=amount1_in,
                amount1_out=amount1_out,
            )
            if reserve0 < 0 or reserve1 < 0:
                blockers.append('pool_history_contains_invalid_swap_amounts')
                break
        else:
            blockers.append('pool_history_contains_unknown_transaction_type')
            break

        effective_history.append(tx)
        states.append({
            'transaction_id': tx.get('transaction_id'),
            'created_at': tx.get('created_at'),
            'transaction_type': tx_type,
            'from_account': tx.get('from_account'),
            'reserve0_after': reserve0,
            'reserve1_after': reserve1,
            'total_supply_after': total_supply,
            'k_last_after': k_last,
        })
        index += 1

    if blockers:
        return None, None, sorted(set(blockers))
    return effective_history, states, []


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
    if not pool_transaction_history:
        return {
            'ok': False,
            'processed_count': 0,
            'blockers': ['missing_pool_transaction_history'],
            'first_failure': {
                'reason': 'missing_pool_transaction_history',
            },
        }

    reserve0 = 0
    reserve1 = 0
    total_supply = 0
    k_last = 0
    processed_count = 0

    def failure(reason: str, tx: dict | None = None, **fields):
        failure_payload = {
            'reason': reason,
            'reserve0_attos_before': _serialize_attos_debug(reserve0),
            'reserve1_attos_before': _serialize_attos_debug(reserve1),
            'total_supply_attos_before': _serialize_attos_debug(total_supply),
            'k_last_before': _serialize_attos_debug(k_last),
        }
        if tx is not None:
            failure_payload.update({
                'transaction_id': tx.get('transaction_id'),
                'transaction_type': tx.get('transaction_type'),
                'created_at': tx.get('created_at'),
                'from_account': tx.get('from_account'),
            })
        for key, value in fields.items():
            if isinstance(value, int):
                failure_payload[key] = _serialize_attos_debug(value)
            else:
                failure_payload[key] = value
        return {
            'ok': False,
            'processed_count': processed_count,
            'blockers': [reason],
            'first_failure': failure_payload,
        }

    index = 0
    while index < len(pool_transaction_history):
        tx = pool_transaction_history[index]
        tx_type = tx.get('transaction_type')
        amount0_in = _to_attos(tx.get('amount_0_in')) or 0
        amount0_out = _to_attos(tx.get('amount_0_out')) or 0
        amount1_in = _to_attos(tx.get('amount_1_in')) or 0
        amount1_out = _to_attos(tx.get('amount_1_out')) or 0
        liquidity = _to_attos(tx.get('liquidity')) or 0

        if tx_type in {'BuyToken0', 'SellToken0'}:
            expected_out = _swap_expected_out_attos(
                tx_type,
                reserve0,
                reserve1,
                amount0_in,
                amount1_in,
            )
            recorded_out = amount0_out if tx_type == 'BuyToken0' else amount1_out
            if expected_out is None or not _swap_out_within_tolerance(
                expected_out,
                recorded_out,
                tolerance=swap_out_tolerance_attos,
            ):
                hidden_swap = _infer_hidden_swap_before_batch(
                    reserve0,
                    reserve1,
                    pool_transaction_history,
                    index,
                )
                if hidden_swap is not None:
                    hidden_type = hidden_swap.get('transaction_type')
                    reserve0, reserve1 = _apply_recorded_swap_attos(
                        hidden_type,
                        reserve0,
                        reserve1,
                        amount0_in=_to_attos(hidden_swap.get('amount_0_in')) or 0,
                        amount0_out=_to_attos(hidden_swap.get('amount_0_out')) or 0,
                        amount1_in=_to_attos(hidden_swap.get('amount_1_in')) or 0,
                        amount1_out=_to_attos(hidden_swap.get('amount_1_out')) or 0,
                    )
                    expected_out = _swap_expected_out_attos(
                        tx_type,
                        reserve0,
                        reserve1,
                        amount0_in,
                        amount1_in,
                    )
                if expected_out is None or not _swap_out_within_tolerance(
                    expected_out,
                    recorded_out,
                    tolerance=swap_out_tolerance_attos,
                ):
                    return failure(
                        'pool_history_contains_invalid_swap_amounts',
                        tx,
                        expected_out_attos=expected_out,
                        recorded_out_attos=recorded_out,
                        swap_out_tolerance_attos=swap_out_tolerance_attos,
                        hidden_swap_inferred=hidden_swap is not None,
                    )

        if tx_type == 'AddLiquidity':
            if reserve0 == 0 and reserve1 == 0:
                expected_liquidity = _sqrt_attos_product(amount0_in, amount1_in)
                if expected_liquidity is None:
                    return failure('pool_history_bootstrap_supply_unknown', tx)
                if virtual_initial_liquidity:
                    if liquidity != 0:
                        return failure(
                            'pool_history_bootstrap_supply_unknown',
                            tx,
                            expected_liquidity_attos=expected_liquidity,
                            recorded_liquidity_attos=liquidity,
                        )
                    total_supply = expected_liquidity
                else:
                    if liquidity != expected_liquidity:
                        return failure(
                            'pool_history_bootstrap_supply_unknown',
                            tx,
                            expected_liquidity_attos=expected_liquidity,
                            recorded_liquidity_attos=liquidity,
                        )
                    total_supply = liquidity
                reserve0 += amount0_in
                reserve1 += amount1_in
                k_last = _sqrt_attos_product(reserve0, reserve1) or 0
            else:
                fee_share = _mint_fee_attos(total_supply, reserve0, reserve1, k_last)
                total_supply += fee_share
                expected_liquidity = min(
                    amount0_in * total_supply // reserve0,
                    amount1_in * total_supply // reserve1,
                )
                if not _attos_within_tolerance(liquidity, expected_liquidity):
                    return failure(
                        'pool_history_liquidity_mint_mismatch',
                        tx,
                        fee_share_attos=fee_share,
                        expected_liquidity_attos=expected_liquidity,
                        recorded_liquidity_attos=liquidity,
                    )
                total_supply += liquidity
                reserve0 += amount0_in
                reserve1 += amount1_in
                k_last = _sqrt_attos_product(reserve0, reserve1) or 0
        elif tx_type == 'RemoveLiquidity':
            fee_share = _mint_fee_attos(total_supply, reserve0, reserve1, k_last)
            total_supply += fee_share
            if liquidity > total_supply or amount0_out > reserve0 or amount1_out > reserve1:
                return failure(
                    'pool_history_remove_liquidity_invalid',
                    tx,
                    fee_share_attos=fee_share,
                    recorded_liquidity_attos=liquidity,
                    amount0_out_attos=amount0_out,
                    amount1_out_attos=amount1_out,
                )
            total_supply -= liquidity
            reserve0 -= amount0_out
            reserve1 -= amount1_out
            k_last = _sqrt_attos_product(reserve0, reserve1) or 0
        elif tx_type in {'BuyToken0', 'SellToken0'}:
            reserve0, reserve1 = _apply_recorded_swap_attos(
                tx_type,
                reserve0,
                reserve1,
                amount0_in=amount0_in,
                amount0_out=amount0_out,
                amount1_in=amount1_in,
                amount1_out=amount1_out,
            )
            if reserve0 < 0 or reserve1 < 0:
                return failure('pool_history_contains_invalid_swap_amounts', tx)
        else:
            return failure('pool_history_contains_unknown_transaction_type', tx)

        processed_count += 1
        index += 1

    return {
        'ok': True,
        'processed_count': processed_count,
        'blockers': [],
        'first_failure': None,
        'swap_out_tolerance_attos': _serialize_attos_debug(swap_out_tolerance_attos),
        'final_state': {
            'reserve0_attos': _serialize_attos_debug(reserve0),
            'reserve1_attos': _serialize_attos_debug(reserve1),
            'total_supply_attos': _serialize_attos_debug(total_supply),
            'k_last': _serialize_attos_debug(k_last),
        },
    }


def _simulate_pool_history(
    pool_transaction_history: list[dict],
    *,
    virtual_initial_liquidity: bool,
) -> tuple[list[dict] | None, list[str]]:
    _, states, blockers = _reconstruct_pool_history(
        pool_transaction_history,
        virtual_initial_liquidity=virtual_initial_liquidity,
    )
    if blockers:
        return None, blockers
    return states, []


def _effective_total_supply_attos_from_state(state: dict) -> int:
    return state['total_supply_after'] + _mint_fee_attos(
        state['total_supply_after'],
        state['reserve0_after'],
        state['reserve1_after'],
        state['k_last_after'],
    )


def _simulate_fee_free_from_open_state(states: list[dict], pool_transaction_history: list[dict], start_index: int) -> tuple[dict, list[str]]:
    reserve0 = states[start_index]['reserve0_after']
    reserve1 = states[start_index]['reserve1_after']
    blockers = []

    for tx in pool_transaction_history[start_index + 1:]:
        tx_type = tx.get('transaction_type')
        if tx_type == 'BuyToken0':
            amount1_in = _to_attos(tx.get('amount_1_in')) or 0
            if amount1_in <= 0:
                blockers.append('pool_history_contains_invalid_swap_amounts')
                continue
            amount0_out = amount1_in * reserve0 // (reserve1 + amount1_in)
            reserve1 += amount1_in
            reserve0 -= amount0_out
        elif tx_type == 'SellToken0':
            amount0_in = _to_attos(tx.get('amount_0_in')) or 0
            if amount0_in <= 0:
                blockers.append('pool_history_contains_invalid_swap_amounts')
                continue
            amount1_out = amount0_in * reserve1 // (reserve0 + amount0_in)
            reserve0 += amount0_in
            reserve1 -= amount1_out
        elif tx_type in {'AddLiquidity', 'RemoveLiquidity'}:
            blockers.append('pool_has_liquidity_changes_after_position_open')
        else:
            blockers.append('pool_history_contains_unknown_transaction_type')

    return {
        'reserve0': reserve0,
        'reserve1': reserve1,
    }, sorted(set(blockers))


def _try_enrich_metrics_with_swap_history(
    partial_metrics: dict,
    *,
    liquidity_history: list[dict],
    pool_transaction_history: list[dict] | None,
    owner_is_fee_to: bool,
) -> tuple[dict | None, list[str]]:
    live_liquidity = _to_decimal(partial_metrics['position_liquidity_live'])
    total_supply = _to_decimal(partial_metrics['total_supply_live'])
    redeemable_amount0 = _to_decimal(partial_metrics['redeemable_amount0'])
    redeemable_amount1 = _to_decimal(partial_metrics['redeemable_amount1'])
    history_liquidity = _history_liquidity(liquidity_history)

    if redeemable_amount0 is None or redeemable_amount1 is None:
        return None, ['missing_live_redeemable_amounts']
    if live_liquidity is None or total_supply is None:
        return None, ['missing_live_liquidity_or_total_supply']

    if not liquidity_history:
        return None, ['missing_liquidity_history']

    effective_history, states, blockers = _reconstruct_pool_history(
        pool_transaction_history or [],
        virtual_initial_liquidity=bool(partial_metrics.get('virtual_initial_liquidity')),
    )
    if blockers:
        return None, blockers

    latest_position_tx = max(
        liquidity_history,
        key=lambda row: (int(row.get('created_at') or 0), int(row.get('transaction_id') or 0)),
    )
    opening_index = None
    for index, state in enumerate(states or []):
        if (
            state['transaction_id'] == latest_position_tx.get('transaction_id')
            and state['created_at'] == latest_position_tx.get('created_at')
        ):
            opening_index = index
            break
    if opening_index is None:
        return None, ['position_open_transaction_missing_from_pool_history']

    fee_to_opening_mint_case = False
    liquidity_basis = live_liquidity
    protocol_fee_amount0 = Decimal('0')
    protocol_fee_amount1 = Decimal('0')
    if live_liquidity is not None and live_liquidity - history_liquidity > EPSILON:
        prior_history_liquidity = _history_liquidity_before(liquidity_history, latest_position_tx)
        fee_to_opening_mint_case = (
            owner_is_fee_to
            and latest_position_tx.get('transaction_type') == 'AddLiquidity'
            and abs(prior_history_liquidity) <= EPSILON
        )
        if not fee_to_opening_mint_case:
            return None, ['liquidity_history_mismatch']
        liquidity_basis = history_liquidity
        protocol_fee_amount0_attos, protocol_fee_amount1_attos = _split_protocol_fee_redeemable_attos(
            redeemable_amount0=redeemable_amount0,
            redeemable_amount1=redeemable_amount1,
            live_liquidity=live_liquidity,
            history_liquidity=history_liquidity,
        )
        protocol_fee_amount0 = _from_attos(protocol_fee_amount0_attos) or Decimal('0')
        protocol_fee_amount1 = _from_attos(protocol_fee_amount1_attos) or Decimal('0')

    if latest_position_tx.get('transaction_type') != 'RemoveLiquidity':
        for tx in (effective_history or [])[:opening_index]:
            if tx.get('transaction_type') in {'BuyToken0', 'SellToken0'}:
                if not fee_to_opening_mint_case:
                    return None, ['pool_has_swaps_before_latest_position_liquidity_change']
                break

    current_total_supply_attos = _to_attos(partial_metrics['total_supply_live'])
    liquidity_basis_attos = _to_attos(liquidity_basis)
    if current_total_supply_attos is None or liquidity_basis_attos is None:
        return None, ['missing_live_liquidity_or_total_supply']
    if not _attos_within_tolerance(
        _effective_total_supply_attos_from_state(states[-1]),
        current_total_supply_attos,
    ):
        return None, ['pool_has_liquidity_changes_after_position_open']
    fee_free_state, blockers = _simulate_fee_free_from_open_state(
        states,
        effective_history or [],
        opening_index,
    )
    if blockers:
        return None, blockers

    principal_amount0 = _from_attos(
        liquidity_basis_attos * fee_free_state['reserve0'] // current_total_supply_attos
    )
    principal_amount1 = _from_attos(
        liquidity_basis_attos * fee_free_state['reserve1'] // current_total_supply_attos
    )
    fee_amount0 = _normalize_non_negative(
        redeemable_amount0 - protocol_fee_amount0 - principal_amount0
    )
    fee_amount1 = _normalize_non_negative(
        redeemable_amount1 - protocol_fee_amount1 - principal_amount1
    )

    if fee_amount0 < 0 or fee_amount1 < 0:
        return None, ['fee_simulation_exceeds_live_redeemable']

    partial_metrics['metrics_status'] = 'exact_swap_history_no_post_open_liquidity_changes'
    partial_metrics['exact_fee_supported'] = True
    partial_metrics['exact_principal_supported'] = True
    partial_metrics['principal_amount0'] = _serialize_decimal(principal_amount0)
    partial_metrics['principal_amount1'] = _serialize_decimal(principal_amount1)
    partial_metrics['fee_amount0'] = _serialize_decimal(fee_amount0)
    partial_metrics['fee_amount1'] = _serialize_decimal(fee_amount1)
    partial_metrics['protocol_fee_amount0'] = _serialize_decimal(protocol_fee_amount0)
    partial_metrics['protocol_fee_amount1'] = _serialize_decimal(protocol_fee_amount1)
    partial_metrics['computation_blockers'] = []
    return partial_metrics, []


def _enrich_metrics_with_history(
    partial_metrics: dict,
    *,
    liquidity_history: list[dict] | None,
    pool_transaction_history: list[dict] | None,
    pool_swap_count_since_open: int | None,
    owner_is_fee_to: bool,
):
    blockers = list(partial_metrics['computation_blockers'])
    liquidity_history = liquidity_history or []

    if not liquidity_history:
        blockers.append('missing_liquidity_history')
        partial_metrics['computation_blockers'] = blockers
        return partial_metrics

    live_liquidity = _to_decimal(partial_metrics['position_liquidity_live'])
    history_liquidity = _history_liquidity(liquidity_history)
    if live_liquidity is None:
        blockers.append('missing_live_liquidity')
    elif abs(live_liquidity - history_liquidity) > Decimal('0.000000000001'):
        blockers.append('liquidity_history_mismatch')

    swap_count = int(pool_swap_count_since_open or 0)
    has_pool_swap_history = any(
        tx.get('transaction_type') in {'BuyToken0', 'SellToken0'}
        for tx in (pool_transaction_history or [])
    )
    if swap_count > 0 or has_pool_swap_history:
        exact_metrics, swap_blockers = _try_enrich_metrics_with_swap_history(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            owner_is_fee_to=owner_is_fee_to,
        )
        if exact_metrics is not None:
            return exact_metrics
        blockers.append('pool_has_swap_history_after_position_open')
        blockers.extend(swap_blockers)
        if 'uniswap_v2_fee_split_not_supported_yet' not in blockers:
            blockers.append('uniswap_v2_fee_split_not_supported_yet')

    redeemable_amount0 = _to_decimal(partial_metrics['redeemable_amount0'])
    redeemable_amount1 = _to_decimal(partial_metrics['redeemable_amount1'])
    if redeemable_amount0 is None or redeemable_amount1 is None:
        blockers.append('missing_live_redeemable_amounts')

    if not blockers:
        partial_metrics['metrics_status'] = 'exact_no_swap_history'
        partial_metrics['exact_fee_supported'] = True
        partial_metrics['exact_principal_supported'] = True
        partial_metrics['principal_amount0'] = _serialize_decimal(redeemable_amount0)
        partial_metrics['principal_amount1'] = _serialize_decimal(redeemable_amount1)
        partial_metrics['fee_amount0'] = '0'
        partial_metrics['fee_amount1'] = '0'
        partial_metrics['protocol_fee_amount0'] = '0'
        partial_metrics['protocol_fee_amount1'] = '0'
    else:
        partial_metrics = _build_estimated_metrics_from_liquidity_history(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            live_liquidity=live_liquidity,
            history_liquidity=history_liquidity,
        )

    partial_metrics['computation_blockers'] = blockers
    return partial_metrics


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
    owner = parse_account(position['owner'])
    url = pool_application_url(swap_base_url, position['pool_application'], in_k8s=in_k8s)
    query = build_position_metrics_query(owner)
    response = await post(
        url=url,
        json=query,
        timeout=(3, 10),
    )
    response.raise_for_status()
    payload = response.json()
    if 'errors' in payload:
        if _graphql_unknown_field(payload, 'totalSupply'):
            legacy_query = build_position_metrics_legacy_query(owner)
            response = await post(
                url=url,
                json=legacy_query,
                timeout=(3, 10),
            )
            response.raise_for_status()
            payload = response.json()
        if 'errors' in payload:
            raise RuntimeError(str(payload['errors']))

    data = payload['data']
    live_transactions = [
        _normalize_live_transaction(tx)
        for tx in (data.get('latestTransactions') or [])
    ]
    if live_transactions:
        pool_transaction_history = _merge_transaction_history(
            pool_transaction_history,
            live_transactions,
        )
        pool_history_gap_summary = _build_transaction_gap_summary(pool_transaction_history)
        liquidity_history = [
            tx
            for tx in (pool_transaction_history or [])
            if tx.get('from_account') == position['owner']
            and tx.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}
        ]
        if liquidity_history:
            latest_position_tx = max(
                liquidity_history,
                key=lambda row: (
                    int(row.get('created_at') or 0),
                    int(row.get('transaction_id') or 0),
                ),
            )
            pool_swap_count_since_open = sum(
                1
                for tx in (pool_transaction_history or [])
                if tx.get('transaction_type') in {'BuyToken0', 'SellToken0'}
                and (
                    int(tx.get('created_at') or 0),
                    int(tx.get('transaction_id') or 0),
                )
                >= (
                    int(latest_position_tx.get('created_at') or 0),
                    int(latest_position_tx.get('transaction_id') or 0),
                )
            )

    liquidity = data.get('liquidity') or {}
    liquidity_value = liquidity.get('liquidity')
    total_supply_value = data.get('totalSupply')
    virtual_initial_liquidity = bool(data.get('virtualInitialLiquidity'))
    owner_is_fee_to = (
        _account_payload_to_string((data.get('pool') or {}).get('fee_to')) == position['owner']
    )
    partial_metrics = _build_partial_metrics(
        liquidity,
        total_supply_value,
        virtual_initial_liquidity,
    )

    if liquidity_value is not None and total_supply_value not in (None, '0'):
        partial_metrics['exact_share_ratio'] = str(
            (Decimal(str(liquidity_value)) / Decimal(str(total_supply_value))).normalize()
        )
    partial_metrics['owner_is_fee_to'] = owner_is_fee_to

    metrics = _enrich_metrics_with_history(
        partial_metrics,
        liquidity_history=liquidity_history,
        pool_transaction_history=pool_transaction_history,
        pool_swap_count_since_open=pool_swap_count_since_open,
        owner_is_fee_to=owner_is_fee_to,
    )
    return _apply_data_quality_warnings(
        metrics,
        pool_history_gap_summary=pool_history_gap_summary,
    )
