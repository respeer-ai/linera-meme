import time
from typing import Optional
import json


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


def serialize_trace_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)


def deserialize_trace_value(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    if stripped[0] not in '{[':
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def persist_http_trace(
    db,
    *,
    source: str,
    component: str,
    operation: str,
    target: str,
    request_url: str,
    request_payload,
    response=None,
    error: str | None = None,
    owner: str | None = None,
    pool_application: str | None = None,
    pool_id: int | None = None,
    details: dict | None = None,
):
    if db is None:
        return

    response_status = None
    response_body = None
    if response is not None:
        response_status = getattr(response, 'status_code', None)
        response_body = getattr(response, 'text', None)

    db.record_debug_trace(
        source=source,
        component=component,
        operation=operation,
        target=target,
        request_url=request_url,
        request_payload=request_payload,
        response_status=response_status,
        response_body=response_body,
        error=error,
        owner=owner,
        pool_application=pool_application,
        pool_id=pool_id,
        details=details,
    )
