from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError


class ClaimBalancesReadModel:
    def __init__(self, repository):
        self.repository = repository

    def get_claim_balances(self, *, owner: str) -> dict:
        payload = self.repository.get_claim_balances(owner=owner)
        if payload is None:
            raise ProjectionQueryUnavailableError('claim_balances')
        return {
            'owner': owner,
            'balances': payload,
        }
