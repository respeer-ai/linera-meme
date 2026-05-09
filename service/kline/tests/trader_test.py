import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from trader import Trader  # noqa: E402
from maker_minute_plan import MinutePlan  # noqa: E402


class FakeDb:
    def __init__(self):
        self.events = []

    def new_maker_event(self, **kwargs):
        self.events.append(kwargs)


class TraderPersistenceTest(unittest.IsolatedAsyncioTestCase):
    def make_pool(self):
        return types.SimpleNamespace(
            pool_id=7,
            token_0='AAA',
            token_1='BBB',
            reserve_0='100',
            reserve_1='200',
            token_0_price='2',
            token_1_price='0.5',
            pool_application=types.SimpleNamespace(short_owner='pool-app'),
            swap=AsyncMock(return_value=True),
        )

    def test_queue_trade_persists_planned_event(self):
        db = FakeDb()
        trader = Trader(
            swap=None,
            wallet=None,
            meme=None,
            proxy=None,
            db=db,
        )
        pool = self.make_pool()

        trader.queue_trade(pool, None, 5.0)

        self.assertEqual(len(db.events), 1)
        self.assertEqual(db.events[0]['event_type'], 'planned')
        self.assertEqual(db.events[0]['pool_id'], 7)
        self.assertEqual(db.events[0]['amount_1'], 5.0)
        self.assertEqual(db.events[0]['quote_notional'], 5.0)

    async def test_execute_pending_in_pool_persists_executed_event(self):
        db = FakeDb()
        wallet = types.SimpleNamespace(
            _chain=lambda: 'wallet-chain',
            account=lambda: 'account',
            balance=AsyncMock(return_value=10.0),
        )
        meme = types.SimpleNamespace(
            creator_chain_id=AsyncMock(return_value='creator-chain'),
            balance=AsyncMock(return_value=100.0),
        )
        trader = Trader(
            swap=None,
            wallet=wallet,
            meme=meme,
            proxy=None,
            db=db,
        )
        pool = self.make_pool()

        executed = await trader.execute_pending_in_pool(pool, 6.0)

        self.assertEqual(executed, 6.0)
        self.assertEqual(len(db.events), 1)
        self.assertEqual(db.events[0]['event_type'], 'executed')
        self.assertEqual(db.events[0]['amount_1'], 6.0)
        self.assertEqual(db.events[0]['quote_notional'], 6.0)
        pool.swap.assert_awaited_once()

    async def test_execute_pending_in_pool_persists_failed_event_when_swap_fails(self):
        db = FakeDb()
        wallet = types.SimpleNamespace(
            _chain=lambda: 'wallet-chain',
            account=lambda: 'account',
            balance=AsyncMock(return_value=10.0),
        )
        meme = types.SimpleNamespace(
            creator_chain_id=AsyncMock(return_value='creator-chain'),
            balance=AsyncMock(return_value=100.0),
        )
        trader = Trader(
            swap=None,
            wallet=wallet,
            meme=meme,
            proxy=None,
            db=db,
        )
        pool = self.make_pool()
        pool.swap = AsyncMock(return_value=False)

        executed = await trader.execute_pending_in_pool(pool, 6.0)

        self.assertEqual(executed, 0.0)
        self.assertEqual(len(db.events), 1)
        self.assertEqual(db.events[0]['event_type'], 'failed')
        self.assertEqual(db.events[0]['details'], '{"reason": "swap_request_failed_or_rejected", "requested_quote_notional": 6.0}')


class TraderExecutionPolicyTest(unittest.TestCase):
    def make_pool(self):
        return types.SimpleNamespace(
            pool_id=8,
            token_0='AAA',
            token_1='BBB',
            reserve_0='100',
            reserve_1='200',
            token_0_price='2',
            token_1_price='0.5',
            pool_application=types.SimpleNamespace(short_owner='pool-app'),
        )

    def test_trade_amounts_buys_token_0_when_reference_price_is_above_pool_price(self):
        trader = Trader(
            swap=None,
            wallet=None,
            meme=None,
            proxy=None,
            db=None,
        )
        pool = self.make_pool()
        state = trader._market_state(pool)
        state.reference_price = 2.2
        state.anchor_price = 2.0
        state.last_price = 2.0

        amount_0, amount_1 = trader.trade_amounts(pool, token_0_balance=100.0, token_1_balance=100.0)

        self.assertIsNone(amount_0)
        self.assertIsNotNone(amount_1)
        self.assertGreater(amount_1, 0.0)

    def test_trade_amounts_sells_token_0_when_reference_price_is_below_pool_price(self):
        trader = Trader(
            swap=None,
            wallet=None,
            meme=None,
            proxy=None,
            db=None,
        )
        pool = self.make_pool()
        state = trader._market_state(pool)
        state.reference_price = 1.8
        state.anchor_price = 2.0
        state.last_price = 2.0

        amount_0, amount_1 = trader.trade_amounts(pool, token_0_balance=100.0, token_1_balance=100.0)

        self.assertIsNotNone(amount_0)
        self.assertGreater(amount_0, 0.0)
        self.assertIsNone(amount_1)

    def test_trade_amounts_uses_market_drift_when_initial_state_has_no_signal(self):
        trader = Trader(
            swap=None,
            wallet=None,
            meme=None,
            proxy=None,
            db=None,
        )
        trader.market_drift = 0.002
        pool = self.make_pool()

        amount_0, amount_1 = trader.trade_amounts(pool, token_0_balance=100.0, token_1_balance=100.0)

        self.assertIsNone(amount_0)
        self.assertIsNotNone(amount_1)
        self.assertGreater(amount_1, 0.0)


class TraderSliceExecutionTest(unittest.IsolatedAsyncioTestCase):
    def make_pool(self):
        return types.SimpleNamespace(
            pool_id=9,
            token_0='AAA',
            token_1='BBB',
            reserve_0='100',
            reserve_1='200',
            token_0_price='2',
            token_1_price='0.5',
            pool_application=types.SimpleNamespace(short_owner='pool-app'),
            swap=AsyncMock(return_value=True),
        )

    async def test_execute_next_slices_consumes_one_slice_per_pool(self):
        trader = Trader(
            swap=None,
            wallet=types.SimpleNamespace(
                _chain=lambda: 'wallet-chain',
                account=lambda: 'account',
                balance=AsyncMock(return_value=10.0),
            ),
            meme=types.SimpleNamespace(
                creator_chain_id=AsyncMock(return_value='creator-chain'),
                balance=AsyncMock(return_value=100.0),
            ),
            proxy=None,
            db=None,
        )
        pool = self.make_pool()
        trader.inventory_controller.set_active_minute_plan(pool.pool_id, MinutePlan(
            quote_notional=6.0,
            slice_quotes=[3.0, 2.0, 1.0],
        ))

        await trader.execute_next_slices([pool])

        self.assertEqual(trader.inventory_controller.active_slice_plan(pool.pool_id), [2.0, 1.0])
        pool.swap.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
