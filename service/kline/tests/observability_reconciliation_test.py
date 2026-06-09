import asyncio
import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.candles import CandlesReadModel  # noqa: E402
from query.read_models.claim_balances import ClaimBalancesReadModel  # noqa: E402
from query.read_models.position_metrics import PositionMetricsReadModel  # noqa: E402
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402
from query.read_models.positions import PositionsReadModel  # noqa: E402
from query.read_models.transactions import TransactionsReadModel  # noqa: E402
from query.read_models.virtual_positions import VirtualPositionsReadModel  # noqa: E402
from query.serializers.claim_balances import ClaimBalancesSerializer  # noqa: E402
from storage.mysql.claim_balance_projection_repo import ClaimBalanceProjectionRepository  # noqa: E402
from storage.mysql.market_stats_projection_repo import MarketStatsProjectionRepository  # noqa: E402
from storage.mysql.settled_trade_projection_repo import SettledTradeProjectionRepository  # noqa: E402


SCALE = Decimal('1000000000000000000')


def raw_amount(value: str) -> str:
    return str(int(Decimal(value) * SCALE))


class ObservabilityReconciliationTest(unittest.TestCase):
    POOL_APPLICATION = '0xpool@chain-a'
    POOL_ID = 7
    TOKEN_0 = 'MEME'
    TOKEN_1 = 'TLINERA'
    OWNER = '0xaaaaaaaa@chain-owner'

    class FakeMetadataResolver:
        def __init__(self, metadata):
            self.metadata = metadata

        def metadata_for_pool_application(self, pool_application):
            return self.metadata.get(pool_application)

        def metadata_by_pool_application(self):
            return dict(self.metadata)

    class FakePoolIdentityProjectionRepository:
        def __init__(self, pool):
            self.pool = dict(pool)

        def resolve_for_read(self, token_0, token_1, *, pool_id=None, pool_application=None):
            if pool_application is not None and pool_application != self.pool['pool_application']:
                raise Exception('Invalid pool application')
            if pool_id is not None and int(pool_id) != int(self.pool['pool_id']):
                raise Exception('Invalid pool id')
            if token_0 == self.pool['token_0'] and token_1 == self.pool['token_1']:
                return (
                    int(self.pool['pool_id']),
                    self.pool['pool_application'],
                    token_0,
                    token_1,
                    False,
                )
            if token_0 == self.pool['token_1'] and token_1 == self.pool['token_0']:
                return (
                    int(self.pool['pool_id']),
                    self.pool['pool_application'],
                    token_0,
                    token_1,
                    True,
                )
            raise Exception('Invalid token pair')

        def resolve_for_tokens(self, token_0, token_1):
            return self.resolve_for_read(token_0, token_1)

    class ProjectionDb:
        def __init__(self, *, trades, now_ms):
            self.trades = list(trades)
            self.current_now_ms = now_ms
            self.cursor_dict = None

        def now_ms(self):
            return self.current_now_ms

        def ensure_fresh_read_connection(self):
            return None

        def fresh_cursor(self, dictionary=False):
            return ObservabilityReconciliationTest.ProjectionCursor(self)

    class ProjectionCursor:
        def __init__(self, db):
            self.db = db
            self.sql = ''
            self.params = ()

        def execute(self, sql, params=()):
            self.sql = sql
            self.params = tuple(params)

        def fetchone(self):
            rows = self.fetchall()
            return rows[0] if rows else None

        def fetchall(self):
            if 'COUNT(*) AS trade_count' in self.sql:
                return [self._summary_row(self._filtered_trades())]
            if 'AS market_watermark_ms' in self.sql:
                rows = self._filtered_trades()
                trade_times = [int(row['trade_time_ms']) for row in rows]
                return [{
                    'market_watermark_ms': max(trade_times) if trade_times else 0,
                }]
            if 'AS trade_watermark_ms' in self.sql:
                rows = self._filtered_trades()
                trade_times = [int(row['trade_time_ms']) for row in rows]
                return [{
                    'trade_watermark_ms': max(trade_times) if trade_times else None,
                }]
            return self._select_rows()

        def close(self):
            return None

        def _select_rows(self):
            rows = self._filtered_trades()
            if 'ORDER BY st.trade_time_ms ASC' in self.sql:
                rows.sort(key=lambda row: (
                    int(row['trade_time_ms']),
                    int(row['transaction_id']),
                    str(row['settled_trade_id']),
                ))
            else:
                rows.sort(key=lambda row: (
                    int(row['trade_time_ms']),
                    int(row['transaction_id']),
                    str(row['settled_trade_id']),
                ), reverse=True)
            limit = self._limit()
            if limit is not None:
                rows = rows[:limit]
            return [self._project_row(row) for row in rows]

        def _project_row(self, row):
            projected = dict(row)
            projected['pool_application'] = projected['pool_application_id']
            return projected

        def _summary_row(self, rows):
            if not rows:
                return {
                    'trade_count': 0,
                    'timestamp_begin': None,
                    'timestamp_end': None,
                }
            times = [int(row['trade_time_ms']) for row in rows]
            return {
                'trade_count': len(rows),
                'timestamp_begin': max(times),
                'timestamp_end': min(times),
            }

        def _filtered_trades(self):
            rows = list(self.db.trades)
            param_index = 0
            if 'FROM raw_blocks rb' in self.sql:
                param_index += 1
            if 'st.pool_application_id = %s' in self.sql:
                pool_application = self.params[param_index]
                param_index += 1
                rows = [
                    row for row in rows
                    if row['pool_application_id'] == pool_application
                ]
            if 'st.trade_time_ms >= %s' in self.sql:
                start_at = int(self.params[param_index])
                param_index += 1
                rows = [
                    row for row in rows
                    if int(row['trade_time_ms']) >= start_at
                ]
            if 'st.trade_time_ms <= %s' in self.sql:
                end_at = int(self.params[param_index])
                param_index += 1
                rows = [
                    row for row in rows
                    if int(row['trade_time_ms']) <= end_at
                ]
            if 'st.trade_time_ms < %s' in self.sql:
                before_ms = int(self.params[param_index])
                param_index += 1
                rows = [
                    row for row in rows
                    if int(row['trade_time_ms']) < before_ms
                ]
            if 'st.transaction_id IN' in self.sql:
                ids = {int(value) for value in self.params[param_index:self._limit_param_index()]}
                rows = [
                    row for row in rows
                    if int(row['transaction_id']) in ids
                ]
            return rows

        def _limit(self):
            if 'LIMIT %s' not in self.sql:
                return None
            return int(self.params[-1])

        def _limit_param_index(self):
            if 'LIMIT %s' in self.sql:
                return len(self.params) - 1
            return len(self.params)

    class ClaimProjectionDb:
        INCOMPLETE_DIAGNOSTICS = {
            'claim_delta_requires_new_transaction_correlation',
            'ambiguous_new_transaction_correlation',
            'missing_pool_token_metadata',
        }

        def __init__(self, *, deltas, diagnostics=None):
            self.deltas = list(deltas)
            self.diagnostics = list(diagnostics or [])

        def ping(self, **_kwargs):
            return None

        def cursor(self, **_kwargs):
            return ObservabilityReconciliationTest.ClaimProjectionCursor(self)

    class ClaimProjectionCursor:
        def __init__(self, db):
            self.db = db
            self.sql = ''
            self.params = ()

        def execute(self, sql, params=()):
            self.sql = sql
            self.params = tuple(params)

        def fetchall(self):
            if 'FROM claim_balance_deltas deltas' not in self.sql:
                return []
            owner = self.params[0]
            groups = {}
            for delta in self.db.deltas:
                if delta['owner'] != owner:
                    continue
                key = (
                    delta['pool_application_id'],
                    delta['execution_chain_id'],
                    delta['token'],
                    delta['owner'],
                )
                group = groups.setdefault(key, {
                    'claimable_raw': Decimal('0'),
                    'claiming_raw': Decimal('0'),
                    'latest_block_height': None,
                    'latest_transaction_index': None,
                    'latest_message_index': None,
                })
                signed_amount = Decimal(delta['delta_amount'])
                if delta['delta_direction'] == 'debit':
                    signed_amount = -signed_amount
                if delta['balance_kind'] == 'claimable':
                    group['claimable_raw'] += signed_amount
                elif delta['balance_kind'] == 'claiming':
                    group['claiming_raw'] += signed_amount
                group['latest_block_height'] = self._max_optional(group['latest_block_height'], delta.get('block_height'))
                group['latest_transaction_index'] = self._max_optional(group['latest_transaction_index'], delta.get('transaction_index'))
                group['latest_message_index'] = self._max_optional(group['latest_message_index'], delta.get('message_index'))

            rows = []
            incomplete_counts = self._incomplete_counts()
            for key, group in groups.items():
                claimable_amount = group['claimable_raw'] / SCALE
                claiming_amount = group['claiming_raw'] / SCALE
                if claimable_amount == 0 and claiming_amount == 0:
                    continue
                pool_application_id, execution_chain_id, token, owner = key
                incomplete_count = incomplete_counts.get((pool_application_id, execution_chain_id), 0)
                rows.append({
                    'pool_application_id': pool_application_id,
                    'execution_chain_id': execution_chain_id,
                    'token': token,
                    'owner': owner,
                    'claimable_amount': self._display_decimal(claimable_amount),
                    'claiming_amount': self._display_decimal(claiming_amount),
                    'latest_block_height': group['latest_block_height'],
                    'latest_transaction_index': group['latest_transaction_index'],
                    'latest_message_index': group['latest_message_index'],
                    'projection_status': 'incomplete' if incomplete_count > 0 else 'complete',
                    'incomplete_diagnostic_count': incomplete_count,
                })
            rows.sort(key=lambda row: (
                row['pool_application_id'],
                row['execution_chain_id'],
                row['token'],
            ))
            return rows

        def close(self):
            return None

        def _incomplete_counts(self):
            counts = {}
            for diagnostic in self.db.diagnostics:
                if diagnostic['diagnostic_type'] not in ObservabilityReconciliationTest.ClaimProjectionDb.INCOMPLETE_DIAGNOSTICS:
                    continue
                key = (diagnostic['pool_application_id'], diagnostic['execution_chain_id'])
                counts[key] = counts.get(key, 0) + 1
            return counts

        def _max_optional(self, current, value):
            if value is None:
                return current
            if current is None or value > current:
                return value
            return current

        def _display_decimal(self, value):
            if value == 0:
                return '0'
            return format(value.normalize(), 'f')

    class FakePositionsRepository:
        def __init__(self, candidates):
            self.candidates = list(candidates)

        def get_positions(self, *, owner, status):
            return []

        def get_owner_candidate_histories(self, *, owner):
            return [
                dict(candidate)
                for candidate in self.candidates
                if candidate['owner'] == owner
            ]

    class FakeSnapshotInputsProjectionRepository:
        class PoolStateProjectionRepository:
            def __init__(self, snapshots):
                self.snapshots = snapshots

            def list_pool_state_snapshots(self):
                return list(self.snapshots)

        def __init__(self, snapshot):
            self.snapshot = dict(snapshot)
            self.pool_state_projection_repo = self.PoolStateProjectionRepository([snapshot['pool_state_snapshot']])

        def get_snapshot_inputs(self, *, owner, pool_application_id, status):
            if pool_application_id != self.snapshot['pool_application']:
                return None
            return PositionMetricsSnapshotInputs({
                'position_basis_snapshot': dict(self.snapshot['position_basis_snapshot']),
                'pool_state_snapshot': dict(self.snapshot['pool_state_snapshot']),
            })

    def setUp(self):
        self.pool = {
            'pool_id': self.POOL_ID,
            'pool_application': self.POOL_APPLICATION,
            'token_0': self.TOKEN_0,
            'token_1': self.TOKEN_1,
        }
        self.metadata = {
            self.POOL_APPLICATION: {
                'pool_id': self.POOL_ID,
                'token_0': self.TOKEN_0,
                'token_1': self.TOKEN_1,
            }
        }
        self.trades = [
            self._trade(
                settled_trade_id='trade-1',
                transaction_id=101,
                trade_time_ms=60_500,
                side='buy_token_0',
                amount_in='20',
                amount_out='10',
            ),
            self._trade(
                settled_trade_id='trade-2',
                transaction_id=102,
                trade_time_ms=90_000,
                side='sell_token_0',
                amount_in='5',
                amount_out='12',
            ),
            self._trade(
                settled_trade_id='trade-3',
                transaction_id=103,
                trade_time_ms=181_000,
                side='buy_token_0',
                amount_in='30',
                amount_out='6',
            ),
        ]
        self.db = self.ProjectionDb(trades=self.trades, now_ms=260_000)
        self.trade_repo = SettledTradeProjectionRepository(
            self.db,
            pool_identity_projection_repo=self.FakePoolIdentityProjectionRepository(self.pool),
            metadata_resolver=self.FakeMetadataResolver(self.metadata),
        )
        self.stats_repo = MarketStatsProjectionRepository(
            self.db,
            metadata_resolver=self.FakeMetadataResolver(self.metadata),
        )

    def test_transactions_candles_stats_and_virtual_positions_reconcile_to_projection_facts(self):
        self._assert_transactions_match_projection_facts()
        self._assert_candles_match_independent_aggregation()
        self._assert_market_stats_match_independent_aggregation()
        self._assert_virtual_positions_and_protocol_fee_metrics_match_projection_facts()
        self._assert_claim_balances_match_projection_facts()

    def _assert_transactions_match_projection_facts(self):
        read_model = TransactionsReadModel(self.trade_repo)

        transactions = read_model.get_transactions(
            token_0=None,
            token_1=None,
            start_at=0,
            end_at=260_000,
        )
        information = read_model.get_information(token_0=None, token_1=None)

        expected = [
            self._expected_transaction(row)
            for row in sorted(
                self.trades,
                key=lambda row: (int(row['trade_time_ms']), int(row['transaction_id'])),
                reverse=True,
            )
        ]
        self.assertEqual([row['transaction_id'] for row in transactions], [row['transaction_id'] for row in expected])
        self.assertEqual(information, {
            'count': len(self.trades),
            'timestamp_begin': 181_000,
            'timestamp_end': 60_500,
        })
        for actual, wanted in zip(transactions, expected):
            self.assertEqual(actual['pool_application'], self.POOL_APPLICATION)
            self.assertEqual(actual['pool_id'], self.POOL_ID)
            self.assertEqual(actual['transaction_type'], wanted['transaction_type'])
            self.assertEqual(actual['direction'], wanted['direction'])
            self.assertFalse(actual['token_reversed'])
            self.assertAlmostEqual(actual['volume'], wanted['base_volume'])
            self.assertAlmostEqual(actual['quote_volume'], wanted['quote_volume'])
            self.assertAlmostEqual(actual['price'], wanted['price'])

    def _assert_candles_match_independent_aggregation(self):
        read_model = CandlesReadModel(self.trade_repo)

        payload = read_model.get_points(
            token_0=self.TOKEN_0,
            token_1=self.TOKEN_1,
            start_at=60_000,
            end_at=240_000,
            interval='1m',
            pool_id=self.POOL_ID,
            pool_application=self.POOL_APPLICATION,
        )

        expected = self._expected_candles(
            rows=self.trades,
            start_at=60_000,
            end_at=240_000,
            market_watermark_ms=181_000,
        )
        self.assertEqual(payload['pool_application'], self.POOL_APPLICATION)
        self.assertEqual(payload['pool_id'], self.POOL_ID)
        self.assertEqual([point['timestamp'] for point in payload['points']], [point['timestamp'] for point in expected])
        for actual, wanted in zip(payload['points'], expected):
            for key in ('open', 'high', 'low', 'close', 'base_volume', 'quote_volume'):
                self.assertAlmostEqual(actual[key], wanted[key])
            self.assertEqual(actual['is_final'], wanted['is_final'])

        carry = next(point for point in payload['points'] if point['timestamp'] == 120_000)
        self.assertEqual(carry['base_volume'], 0.0)
        self.assertEqual(carry['quote_volume'], 0.0)
        self.assertEqual(carry['open'], carry['close'])

    def _assert_claim_balances_match_projection_facts(self):
        self._assert_single_claim_balance_delta_reconciles()
        self._assert_consecutive_claim_balance_deltas_reconcile()

    def _assert_single_claim_balance_delta_reconciles(self):
        payload = self._claim_balances_payload([
            self._claim_delta(
                delta_id='single-native-credit',
                token='native',
                balance_kind='claimable',
                amount='7.5',
                direction='credit',
                block_height=41,
                transaction_index=2,
                message_index=0,
            ),
        ])

        self.assertEqual(payload['owner'], self.OWNER)
        self.assertEqual(len(payload['balances']), 1)
        balance = payload['balances'][0]
        self.assertEqual(balance['token'], 'native')
        self.assertEqual(balance['claimable_amount'], '7.5')
        self.assertEqual(balance['claiming_amount'], '0')
        self.assertEqual(balance['projection_status'], 'complete')
        self.assertEqual(balance['diagnostics'], {'incomplete_count': 0})
        self.assertEqual(balance['latest_block_height'], 41)
        self.assertEqual(balance['latest_transaction_index'], 2)
        self.assertEqual(balance['latest_message_index'], 0)

    def _assert_consecutive_claim_balance_deltas_reconcile(self):
        payload = self._claim_balances_payload([
            self._claim_delta(
                delta_id='native-credit-swap-output',
                token='native',
                balance_kind='claimable',
                amount='10',
                direction='credit',
                block_height=50,
                transaction_index=1,
                message_index=0,
            ),
            self._claim_delta(
                delta_id='native-credit-remove-output',
                token='native',
                balance_kind='claimable',
                amount='2.5',
                direction='credit',
                block_height=51,
                transaction_index=1,
                message_index=0,
            ),
            self._claim_delta(
                delta_id='native-claim-start-debit',
                token='native',
                balance_kind='claimable',
                amount='4',
                direction='debit',
                block_height=52,
                transaction_index=2,
                message_index=0,
            ),
            self._claim_delta(
                delta_id='native-claim-start-claiming-credit',
                token='native',
                balance_kind='claiming',
                amount='4',
                direction='credit',
                block_height=52,
                transaction_index=2,
                message_index=0,
            ),
            self._claim_delta(
                delta_id='native-claim-receipt-success',
                token='native',
                balance_kind='claiming',
                amount='1.5',
                direction='debit',
                block_height=53,
                transaction_index=3,
                message_index=1,
            ),
            self._claim_delta(
                delta_id='meme-credit-add-liquidity-excess',
                token=self.TOKEN_0,
                balance_kind='claimable',
                amount='3.25',
                direction='credit',
                block_height=54,
                transaction_index=1,
                message_index=0,
            ),
        ])

        by_token = {balance['token']: balance for balance in payload['balances']}
        self.assertEqual(set(by_token), {'native', self.TOKEN_0})
        self.assertEqual(by_token['native']['claimable_amount'], '8.5')
        self.assertEqual(by_token['native']['claiming_amount'], '2.5')
        self.assertEqual(by_token['native']['projection_status'], 'complete')
        self.assertEqual(by_token['native']['latest_block_height'], 53)
        self.assertEqual(by_token['native']['latest_transaction_index'], 3)
        self.assertEqual(by_token['native']['latest_message_index'], 1)
        self.assertEqual(by_token[self.TOKEN_0]['claimable_amount'], '3.25')
        self.assertEqual(by_token[self.TOKEN_0]['claiming_amount'], '0')
        self.assertEqual(by_token[self.TOKEN_0]['projection_status'], 'complete')

    def _claim_balances_payload(self, deltas, diagnostics=None):
        repository = ClaimBalanceProjectionRepository(
            self.ClaimProjectionDb(deltas=deltas, diagnostics=diagnostics),
        )
        read_model_payload = ClaimBalancesReadModel(repository).get_claim_balances(owner=self.OWNER)
        return ClaimBalancesSerializer().serialize_claim_balances(read_model_payload)

    def _claim_delta(
        self,
        *,
        delta_id,
        token,
        balance_kind,
        amount,
        direction,
        block_height,
        transaction_index,
        message_index,
    ):
        return {
            'claim_balance_delta_id': delta_id,
            'normalized_event_id': f'event-{delta_id}',
            'pool_application_id': self.POOL_APPLICATION,
            'execution_chain_id': 'chain-a',
            'token': token,
            'owner': self.OWNER,
            'balance_kind': balance_kind,
            'delta_amount': raw_amount(amount),
            'delta_direction': direction,
            'block_height': block_height,
            'transaction_index': transaction_index,
            'message_index': message_index,
            'derivation_source': 'e2e_projection_fact',
            'derivation_confidence': 'exact',
            'source_event_key': f'source-{delta_id}',
            'event_payload_json': {},
        }

    def _assert_market_stats_match_independent_aggregation(self):
        pool_stats = self.stats_repo.get_pool_stats(interval='1d')
        protocol_stats = self.stats_repo.get_protocol_stats(
            pools=[{
                'pool_id': self.POOL_ID,
                'pool_application': self.POOL_APPLICATION,
                'token_0': self.TOKEN_0,
                'token_1': self.TOKEN_1,
                'current_reserve_0': '21',
                'current_reserve_1': '72',
            }]
        )

        expected_volume = sum((self._quote_volume(row) for row in self.trades), Decimal('0'))
        expected_prices = [self._price(row) for row in self.trades]
        expected_tvl = Decimal('72') * Decimal('2')
        meme_native_price = Decimal('72') / Decimal('21')
        expected_fees = (
            Decimal('20') * Decimal('0.003')
            + Decimal('5') * Decimal('0.003') * meme_native_price
            + Decimal('30') * Decimal('0.003')
        )

        self.assertEqual(len(pool_stats), 1)
        self.assertEqual(pool_stats[0]['pool_application'], self.POOL_APPLICATION)
        self.assertAlmostEqual(pool_stats[0]['volume'], float(expected_volume))
        self.assertEqual(pool_stats[0]['tx_count'], len(self.trades))
        self.assertAlmostEqual(pool_stats[0]['high'], float(max(expected_prices)))
        self.assertAlmostEqual(pool_stats[0]['low'], float(min(expected_prices)))
        self.assertAlmostEqual(protocol_stats['volume'], float(expected_volume))
        self.assertEqual(protocol_stats['tx_count'], len(self.trades))
        self.assertAlmostEqual(protocol_stats['fees'], float(expected_fees))
        self.assertAlmostEqual(protocol_stats['tvl'], float(expected_tvl))

    def _assert_virtual_positions_and_protocol_fee_metrics_match_projection_facts(self):
        position_basis_snapshot = {
            'status': 'active',
            'basis_type': 'virtual_initial_liquidity',
            'current_liquidity': '0',
            'basis_amount_0': '105',
            'basis_amount_1': '0',
            'semantic_facts': {
                'full_protocol_fee_liquidity_owned_by_current_owner': '10',
                'full_protocol_fee_current_owner_provenance_case': 'all_mints_owned_by_current_owner',
            },
        }
        pool_state_snapshot = {
            'pool_application_id': self.POOL_APPLICATION,
            'last_trade_time_ms': 181_000,
            'last_liquidity_event_time_ms': 50_000,
            'current_reserve_0': '120',
            'current_reserve_1': '90',
            'current_total_supply': '110',
            'fee_free_total_supply': '100',
            'state_payload_json': {
                'virtual_initial_liquidity': True,
                'fee_to_account_latest_known': self.OWNER,
                'fee_free_basis': {
                    'from_account': self.OWNER,
                    'reserve0_after': raw_amount('105'),
                    'reserve1_after': raw_amount('0'),
                },
                'pool_created_metadata': {
                    'token_0': self.TOKEN_0,
                    'token_1': self.TOKEN_1,
                },
            },
        }
        positions_repository = self.FakePositionsRepository([{
            'pool_application': self.POOL_APPLICATION,
            'pool_id': self.POOL_ID,
            'token_0': self.TOKEN_0,
            'token_1': self.TOKEN_1,
            'owner': self.OWNER,
            'opened_at': None,
            'updated_at': 50_000,
            'add_tx_count': 0,
            'virtual_initial_amount0': '105',
            'virtual_initial_amount1': '0',
        }])
        snapshot_repository = self.FakeSnapshotInputsProjectionRepository({
            'pool_application': self.POOL_APPLICATION,
            'position_basis_snapshot': position_basis_snapshot,
            'pool_state_snapshot': pool_state_snapshot,
        })
        virtual_read_model = VirtualPositionsReadModel(
            projection_repository=positions_repository,
            snapshot_inputs_projection_repository=snapshot_repository,
        )

        positions = asyncio.run(PositionsReadModel(
            positions_repository,
            virtual_positions_read_model=virtual_read_model,
        ).get_positions(owner=self.OWNER, status='all'))['positions']
        metrics = asyncio.run(PositionMetricsReadModel(
            positions_repository,
            fetcher=self._unexpected_chain_query_fetcher,
            virtual_positions_read_model=virtual_read_model,
        ).get_position_metrics(owner=self.OWNER, status='all')).public_payload()['metrics']

        self.assertEqual(len(positions), 1)
        position = positions[0]
        self.assertEqual(position['status'], 'virtual')
        self.assertEqual(position['position_kind'], 'virtual_initial_liquidity')
        self.assertEqual(position['virtual_initial_amount0'], '105')
        self.assertEqual(position['virtual_initial_amount1'], '0')
        self.assertEqual(position['protocol_fee_receiver_account'], self.OWNER)

        self.assertEqual(len(metrics), 1)
        metric = metrics[0]
        expected_protocol_fee_ratio = Decimal('10') / Decimal('110')
        self.assertEqual(metric['position_liquidity'], '10')
        self.assertEqual(metric['total_supply'], '110')
        self.assertEqual(metric['share_ratio'], '0.090909090909090909')
        self.assertEqual(metric['protocol_fee_amount0'], self._serialize_decimal(Decimal('120') * expected_protocol_fee_ratio))
        self.assertEqual(metric['protocol_fee_amount1'], self._serialize_decimal(Decimal('90') * expected_protocol_fee_ratio))
        self.assertNotIn('owner_receives_protocol_fees', metric)
        self.assertNotIn('fee_calculation_complete', metric)

    async def _unexpected_chain_query_fetcher(self, _position):
        raise AssertionError('observability product test must not query chain metrics outside projections')

    def _trade(self, *, settled_trade_id, transaction_id, trade_time_ms, side, amount_in, amount_out):
        row = {
            'pool_application_id': self.POOL_APPLICATION,
            'settled_trade_id': settled_trade_id,
            'transaction_id': transaction_id,
            'trade_time_ms': trade_time_ms,
            'side': side,
            'from_account': '0xmaker@chain-maker',
            'amount_in': raw_amount(amount_in),
            'amount_out': raw_amount(amount_out),
            'event_payload_json': {},
        }
        if side == 'buy_token_0':
            row.update({
                'amount_0_in': None,
                'amount_0_out': raw_amount(amount_out),
                'amount_1_in': raw_amount(amount_in),
                'amount_1_out': None,
            })
        else:
            row.update({
                'amount_0_in': raw_amount(amount_in),
                'amount_0_out': None,
                'amount_1_in': None,
                'amount_1_out': raw_amount(amount_out),
            })
        return row

    def _expected_transaction(self, row):
        base_volume = self._base_volume(row)
        quote_volume = self._quote_volume(row)
        return {
            'transaction_id': int(row['transaction_id']),
            'transaction_type': 'BuyToken0' if row['side'] == 'buy_token_0' else 'SellToken0',
            'direction': 'Buy' if row['side'] == 'buy_token_0' else 'Sell',
            'base_volume': float(base_volume),
            'quote_volume': float(quote_volume),
            'price': float(Decimal('0') if base_volume == 0 else quote_volume / base_volume),
        }

    def _expected_candles(self, *, rows, start_at, end_at, market_watermark_ms):
        buckets = {}
        for row in rows:
            timestamp = int(row['trade_time_ms'])
            if timestamp < start_at or timestamp > end_at:
                continue
            bucket_start = timestamp // 60_000 * 60_000
            point = self._expected_transaction(row)
            bucket = buckets.setdefault(bucket_start, [])
            bucket.append({
                'transaction_id': int(row['transaction_id']),
                'trade_time_ms': timestamp,
                **point,
            })

        points = []
        last_close = None
        bucket_start = start_at // 60_000 * 60_000
        end_bucket = end_at // 60_000 * 60_000
        while bucket_start <= end_bucket:
            trades = sorted(
                buckets.get(bucket_start, []),
                key=lambda row: (row['trade_time_ms'], row['transaction_id']),
            )
            if trades:
                prices = [trade['price'] for trade in trades]
                close = trades[-1]['price']
                points.append({
                    'timestamp': bucket_start,
                    'open': trades[0]['price'],
                    'high': max(prices),
                    'low': min(prices),
                    'close': close,
                    'base_volume': sum(trade['base_volume'] for trade in trades),
                    'quote_volume': sum(trade['quote_volume'] for trade in trades),
                    'is_final': market_watermark_ms > bucket_start + 60_000 - 1,
                })
                last_close = close
            elif last_close is not None and market_watermark_ms > bucket_start + 60_000 - 1:
                points.append({
                    'timestamp': bucket_start,
                    'open': last_close,
                    'high': last_close,
                    'low': last_close,
                    'close': last_close,
                    'base_volume': 0.0,
                    'quote_volume': 0.0,
                    'is_final': True,
                })
            bucket_start += 60_000
        return points

    def _base_volume(self, row):
        if row['side'] == 'buy_token_0':
            return Decimal(row['amount_out']) / SCALE
        return Decimal(row['amount_in']) / SCALE

    def _quote_volume(self, row):
        if row['side'] == 'buy_token_0':
            return Decimal(row['amount_in']) / SCALE
        return Decimal(row['amount_out']) / SCALE

    def _price(self, row):
        base_volume = self._base_volume(row)
        if base_volume == 0:
            return Decimal('0')
        return self._quote_volume(row) / base_volume

    def _serialize_decimal(self, value):
        if value == 0:
            return '0'
        return format(value.quantize(Decimal('0.000000000000000001')).normalize(), 'f')


if __name__ == '__main__':
    unittest.main()
