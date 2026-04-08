import time
from typing import Optional


def now_ms() -> int:
    return int(time.time() * 1000)


def build_api_request_log_line(event: str, **fields) -> str:
    parts = [f'[kline-api] event={event}']
    for key in sorted(fields.keys()):
        parts.append(f'{key}={fields[key]}')
    return ' '.join(parts)


def build_api_trace_context(request_id: Optional[str], raw_start_at: int, raw_end_at: int, interval: str):
    return {
        'request_id': request_id if request_id else 'missing',
        'raw_start_at': raw_start_at,
        'raw_end_at': raw_end_at,
        'interval': interval,
        'received_at_ms': now_ms(),
    }
