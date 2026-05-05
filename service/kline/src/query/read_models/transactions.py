from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError


class TransactionsReadModel:
    def __init__(self, repository):
        self.repository = repository

    def get_transactions(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
        start_at: int,
        end_at: int,
    ) -> list[dict]:
        payload = self.repository.get_transactions(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
        )
        if payload is None:
            raise ProjectionQueryUnavailableError('transactions')
        return payload

    def get_information(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
    ) -> dict:
        payload = self.repository.get_transactions_information(
            token_0=token_0,
            token_1=token_1,
        )
        if payload is None:
            raise ProjectionQueryUnavailableError('transactions_information')
        return payload
