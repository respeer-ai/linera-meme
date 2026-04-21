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


if __name__ == '__main__':
    unittest.main()
