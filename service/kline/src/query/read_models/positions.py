class PositionsReadModel:
    def __init__(self, repository):
        self.repository = repository

    def get_positions(
        self,
        *,
        owner: str,
        status: str,
    ) -> dict:
        return {
            'owner': owner,
            'positions': self.repository.get_positions(owner=owner, status=status),
        }
