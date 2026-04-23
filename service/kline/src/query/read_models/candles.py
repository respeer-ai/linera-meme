class CandlesReadModel:
    def __init__(self, repository):
        self.repository = repository

    def get_points(
        self,
        *,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> dict:
        resolved_pool_id, resolved_pool_application, resolved_token_0, resolved_token_1, points = self.repository.get_candles(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        return {
            'pool_id': resolved_pool_id,
            'pool_application': resolved_pool_application,
            'token_0': resolved_token_0,
            'token_1': resolved_token_1,
            'interval': interval,
            'start_at': start_at,
            'end_at': end_at,
            'points': points,
        }

    def get_information(
        self,
        *,
        token_0: str,
        token_1: str,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> dict:
        return self.repository.get_candles_information(
            token_0=token_0,
            token_1=token_1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
