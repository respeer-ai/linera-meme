class ProjectionRepository:
    """Bridge phase-1 query models onto the existing Db implementation."""

    def __init__(self, db):
        self.db = db

    def get_candles(
        self,
        *,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> tuple[int | None, str | None, str, str, list[dict]]:
        return self.db.get_kline(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )

    def get_candles_information(
        self,
        *,
        token_0: str,
        token_1: str,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> dict:
        return self.db.get_kline_information(
            token_0=token_0,
            token_1=token_1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )

    def get_transactions(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
        start_at: int,
        end_at: int,
    ) -> list[dict]:
        return self.db.get_transactions(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
        )

    def get_transactions_information(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
    ) -> dict:
        return self.db.get_transactions_information(
            token_0=token_0,
            token_1=token_1,
        )

    def get_positions(
        self,
        *,
        owner: str,
        status: str,
    ) -> list[dict]:
        return self.db.get_positions(owner=owner, status=status)
