import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.pool_identity_projection_repo import PoolIdentityProjectionRepository  # noqa: E402


class PoolIdentityProjectionRepositoryTest(unittest.TestCase):
    class FakeCursor:
        def __init__(self):
            self.executed = []
            self.responses = []

        def execute(self, sql, params=()):
            self.executed.append((sql, params))

        def fetchall(self):
            if self.responses:
                return list(self.responses.pop(0))
            return []

        def fetchone(self):
            rows = self.fetchall()
            if not rows:
                return None
            return rows[0]

    class FakeDb:
        def __init__(self):
            self.cursor_dict = PoolIdentityProjectionRepositoryTest.FakeCursor()
            self.calls = []
            self.pools_table = 'pools'

        def ensure_fresh_read_connection(self):
            self.calls.append('ensure_fresh_read_connection')

    def test_resolve_for_tokens_prefers_forward_match(self):
        db = self.FakeDb()
        db.cursor_dict.responses = [[{
            'pool_id': 7,
            'pool_application': 'chain-a:pool-app',
            'token_0': 'AAA',
            'token_1': 'BBB',
        }]]
        repository = PoolIdentityProjectionRepository(db)

        resolved = repository.resolve_for_tokens('AAA', 'BBB')

        self.assertEqual(resolved, (7, 'chain-a:pool-app', 'AAA', 'BBB', False))

    def test_resolve_for_tokens_uses_reverse_match_when_needed(self):
        db = self.FakeDb()
        db.cursor_dict.responses = [
            [],
            [{
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'BBB',
                'token_1': 'AAA',
            }],
        ]
        repository = PoolIdentityProjectionRepository(db)

        resolved = repository.resolve_for_tokens('AAA', 'BBB')

        self.assertEqual(resolved, (7, 'chain-a:pool-app', 'AAA', 'BBB', True))

    def test_resolve_for_read_uses_pool_id_and_validates_token_order(self):
        db = self.FakeDb()
        db.cursor_dict.responses = [[{
            'pool_id': 7,
            'pool_application': 'chain-a:pool-app',
            'token_0': 'BBB',
            'token_1': 'AAA',
        }]]
        repository = PoolIdentityProjectionRepository(db)

        resolved = repository.resolve_for_read(
            'AAA',
            'BBB',
            pool_id=7,
            pool_application='chain-a:pool-app',
        )

        self.assertEqual(resolved, (7, 'chain-a:pool-app', 'AAA', 'BBB', True))

    def test_resolve_for_read_defaults_native_token(self):
        db = self.FakeDb()
        db.cursor_dict.responses = [[{
            'pool_id': 3,
            'pool_application': 'chain-a:native-pool',
            'token_0': 'TLINERA',
            'token_1': 'MEME',
        }]]
        repository = PoolIdentityProjectionRepository(db)

        resolved = repository.resolve_for_read(None, 'MEME', pool_id=3)

        self.assertEqual(resolved, (3, 'chain-a:native-pool', 'TLINERA', 'MEME', False))

    def test_resolve_for_tokens_rejects_unknown_pair(self):
        db = self.FakeDb()
        db.cursor_dict.responses = [[], []]
        repository = PoolIdentityProjectionRepository(db)

        with self.assertRaisesRegex(Exception, 'Invalid token pair'):
            repository.resolve_for_tokens('AAA', 'BBB')
