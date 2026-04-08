import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from request_trace import build_api_request_log_line, build_api_trace_context  # noqa: E402


class RequestTraceTest(unittest.TestCase):
    def test_build_api_request_log_line_orders_fields_for_stable_grep(self):
        self.assertEqual(
            build_api_request_log_line('received', request_id='abc', aligned_start_at=1, aligned_end_at=2),
            '[kline-api] event=received aligned_end_at=2 aligned_start_at=1 request_id=abc',
        )

    def test_build_api_trace_context_preserves_raw_window_and_request_id(self):
        with patch('request_trace.now_ms', return_value=1_800_000_000_123):
            trace = build_api_trace_context('req-7', 1000, 2000, '1min')

        self.assertEqual(trace, {
            'request_id': 'req-7',
            'raw_start_at': 1000,
            'raw_end_at': 2000,
            'interval': '1min',
            'received_at_ms': 1_800_000_000_123,
        })


if __name__ == '__main__':
    unittest.main()
