import time


class WebsocketCandleReader:
    _WINDOW_SECONDS_BY_INTERVAL = {
        '1min': 60 * 5,
        '5min': 300 * 3,
        '10min': 600 * 3,
        '1h': 3600 * 3,
        '1D': 86400 * 3,
        '1W': 86400 * 7 * 4,
        '1ME': 86400 * 30 * 12,
    }

    def __init__(self, candles_read_model):
        self.candles_read_model = candles_read_model

    def get_last_points(
        self,
        *,
        token_0: str,
        token_1: str,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> dict:
        resolved_interval = (
            interval
            if interval in self._WINDOW_SECONDS_BY_INTERVAL
            else '5min'
        )
        end_at_seconds = int(time.time() // 60 * 60)
        start_at_seconds = end_at_seconds - self._WINDOW_SECONDS_BY_INTERVAL[resolved_interval]
        start_at = start_at_seconds * 1000
        end_at = end_at_seconds * 1000
        payload = self.candles_read_model.get_points(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            interval=resolved_interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        payload['start_at'] = start_at
        payload['end_at'] = end_at
        return payload
