import async_request
from environment import running_in_k8s
from decimal import Decimal
import math

EPSILON = Decimal('0.000000000001')
DISPLAY_QUANTUM = Decimal('0.000000000000000001')
ATTOS_SCALE = 10 ** 18


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
            }
        ''',
        'variables': {
            'owner': owner,
        },
    }


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


def _to_attos(value) -> int | None:
    if value is None:
        return None
    return int((Decimal(str(value)) * ATTOS_SCALE).to_integral_value())


def _from_attos(value: int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value) / Decimal(ATTOS_SCALE)


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
        'computation_blockers': [],
        'principal_amount0': None,
        'principal_amount1': None,
        'fee_amount0': None,
        'fee_amount1': None,
    }


def _history_liquidity(liquidity_history: list[dict]) -> Decimal:
    current_liquidity = Decimal('0')
    for row in liquidity_history:
        liquidity = _to_decimal(row.get('liquidity')) or Decimal('0')
        if row.get('transaction_type') == 'AddLiquidity':
            current_liquidity += liquidity
        elif row.get('transaction_type') == 'RemoveLiquidity':
            current_liquidity -= liquidity
    return current_liquidity


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
    if value < 0 and abs(value) <= tolerance:
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


def _simulate_pool_history(pool_transaction_history: list[dict]) -> tuple[list[dict] | None, list[str]]:
    if not pool_transaction_history:
        return None, ['missing_pool_transaction_history']

    reserve0 = 0
    reserve1 = 0
    total_supply = 0
    k_last = 0
    states = []
    blockers = []

    for tx in pool_transaction_history:
        tx_type = tx.get('transaction_type')
        amount0_in = _to_attos(tx.get('amount_0_in')) or 0
        amount0_out = _to_attos(tx.get('amount_0_out')) or 0
        amount1_in = _to_attos(tx.get('amount_1_in')) or 0
        amount1_out = _to_attos(tx.get('amount_1_out')) or 0
        liquidity = _to_attos(tx.get('liquidity')) or 0

        if tx_type == 'AddLiquidity':
            if reserve0 == 0 and reserve1 == 0:
                expected_liquidity = _sqrt_attos_product(amount0_in, amount1_in)
                if expected_liquidity is None or liquidity != expected_liquidity:
                    blockers.append('pool_history_bootstrap_supply_unknown')
                    continue
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
                if liquidity != expected_liquidity:
                    blockers.append('pool_history_liquidity_mint_mismatch')
                    continue
                total_supply += liquidity
                reserve0 += amount0_in
                reserve1 += amount1_in
                k_last = _sqrt_attos_product(reserve0, reserve1) or 0
        elif tx_type == 'RemoveLiquidity':
            fee_share = _mint_fee_attos(total_supply, reserve0, reserve1, k_last)
            total_supply += fee_share
            if liquidity > total_supply or amount0_out > reserve0 or amount1_out > reserve1:
                blockers.append('pool_history_remove_liquidity_invalid')
                continue
            total_supply -= liquidity
            reserve0 -= amount0_out
            reserve1 -= amount1_out
            k_last = _sqrt_attos_product(reserve0, reserve1) or 0
        elif tx_type in {'BuyToken0', 'SellToken0'}:
            reserve0 = reserve0 + amount0_in - amount0_out
            reserve1 = reserve1 + amount1_in - amount1_out
            if reserve0 < 0 or reserve1 < 0:
                blockers.append('pool_history_contains_invalid_swap_amounts')
                continue
        else:
            blockers.append('pool_history_contains_unknown_transaction_type')
            continue

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

    if blockers:
        return None, sorted(set(blockers))
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

    states, blockers = _simulate_pool_history(pool_transaction_history or [])
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

    if latest_position_tx.get('transaction_type') != 'RemoveLiquidity':
        for tx in (pool_transaction_history or [])[:opening_index]:
            if tx.get('transaction_type') in {'BuyToken0', 'SellToken0'}:
                if not fee_to_opening_mint_case:
                    return None, ['pool_has_swaps_before_latest_position_liquidity_change']
                break

    current_total_supply_attos = _to_attos(partial_metrics['total_supply_live'])
    liquidity_basis_attos = _to_attos(liquidity_basis)
    if current_total_supply_attos is None or liquidity_basis_attos is None:
        return None, ['missing_live_liquidity_or_total_supply']
    if _effective_total_supply_attos_from_state(states[-1]) != current_total_supply_attos:
        return None, ['pool_has_liquidity_changes_after_position_open']
    fee_free_state, blockers = _simulate_fee_free_from_open_state(
        states,
        pool_transaction_history or [],
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
    fee_amount0 = _normalize_non_negative(redeemable_amount0 - principal_amount0)
    fee_amount1 = _normalize_non_negative(redeemable_amount1 - principal_amount1)

    if fee_amount0 < 0 or fee_amount1 < 0:
        return None, ['fee_simulation_exceeds_live_redeemable']

    partial_metrics['metrics_status'] = 'exact_swap_history_no_post_open_liquidity_changes'
    partial_metrics['exact_fee_supported'] = True
    partial_metrics['exact_principal_supported'] = True
    partial_metrics['principal_amount0'] = _serialize_decimal(principal_amount0)
    partial_metrics['principal_amount1'] = _serialize_decimal(principal_amount1)
    partial_metrics['fee_amount0'] = _serialize_decimal(fee_amount0)
    partial_metrics['fee_amount1'] = _serialize_decimal(fee_amount1)
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
    else:
        partial_metrics['metrics_status'] = 'partial_live_redeemable_only'

    partial_metrics['computation_blockers'] = blockers
    return partial_metrics


async def fetch_live_position_metrics(
    position: dict,
    swap_base_url: str,
    *,
    liquidity_history: list[dict] | None = None,
    pool_transaction_history: list[dict] | None = None,
    pool_swap_count_since_open: int | None = None,
    post=async_request.post,
    in_k8s: bool | None = None,
):
    query = build_position_metrics_query(parse_account(position['owner']))
    response = await post(
        url=pool_application_url(swap_base_url, position['pool_application'], in_k8s=in_k8s),
        json=query,
        timeout=(3, 10),
    )
    response.raise_for_status()
    payload = response.json()
    if 'errors' in payload:
        raise RuntimeError(str(payload['errors']))

    data = payload['data']
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

    return _enrich_metrics_with_history(
        partial_metrics,
        liquidity_history=liquidity_history,
        pool_transaction_history=pool_transaction_history,
        pool_swap_count_since_open=pool_swap_count_since_open,
        owner_is_fee_to=owner_is_fee_to,
    )
