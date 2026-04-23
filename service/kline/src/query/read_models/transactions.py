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
        return self.repository.get_transactions(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
        )

    def get_information(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
    ) -> dict:
        return self.repository.get_transactions_information(
            token_0=token_0,
            token_1=token_1,
        )
