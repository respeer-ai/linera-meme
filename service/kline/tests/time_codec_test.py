import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from time_codec import TimeCodec  # noqa: E402


class TimeCodecTest(unittest.TestCase):
    def test_event_time_ms_from_transaction_prefers_created_at_micros(self):
        codec = TimeCodec()

        self.assertEqual(
            codec.event_time_ms_from_transaction(
                {
                    'created_at_micros': 1234000,
                    'created_at': 9999,
                }
            ),
            1234,
        )

    def test_event_time_ms_from_transaction_falls_back_to_created_at_ms(self):
        codec = TimeCodec()

        self.assertEqual(
            codec.event_time_ms_from_transaction(
                {
                    'created_at': 5678,
                }
            ),
            5678,
        )

    def test_row_time_ms_returns_first_present_key(self):
        codec = TimeCodec()

        self.assertEqual(
            codec.row_time_ms(
                {
                    'event_time_ms': 4567,
                    'created_at': 1234,
                },
                'created_at',
                'event_time_ms',
            ),
            1234,
        )
        self.assertEqual(
            codec.row_time_ms(
                {
                    'event_time_ms': 4567,
                },
                'created_at',
                'event_time_ms',
            ),
            4567,
        )


if __name__ == '__main__':
    unittest.main()
