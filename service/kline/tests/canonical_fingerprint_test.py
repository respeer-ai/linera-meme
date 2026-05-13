import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.canonical_fingerprint import CanonicalFingerprint  # noqa: E402


class CanonicalFingerprintTest(unittest.TestCase):
    def test_build_is_stable_across_key_order_and_bytes(self):
        fingerprint = CanonicalFingerprint()

        left = fingerprint.build({
            'b': 2,
            'a': {'y': b'hello', 'x': 1},
        })
        right = fingerprint.build({
            'a': {'x': 1, 'y': b'hello'},
            'b': 2,
        })

        self.assertEqual(left, right)

    def test_build_distinguishes_different_payloads(self):
        fingerprint = CanonicalFingerprint()

        left = fingerprint.build({'value': b'hello'})
        right = fingerprint.build({'value': b'world'})

        self.assertNotEqual(left, right)

    def test_build_treats_bytes_like_values_identically(self):
        fingerprint = CanonicalFingerprint()

        left = fingerprint.build({'value': b'hello'})
        right = fingerprint.build({'value': bytearray(b'hello')})
        third = fingerprint.build({'value': memoryview(b'hello')})

        self.assertEqual(left, right)
        self.assertEqual(right, third)

    def test_build_bytes_uses_ascii_canonical_json_payload(self):
        fingerprint = CanonicalFingerprint()
        payload = {'b': 2, 'a': {'raw': b'abc'}}

        self.assertEqual(
            fingerprint.build_bytes(payload),
            fingerprint.build_json(payload).encode('ascii'),
        )
