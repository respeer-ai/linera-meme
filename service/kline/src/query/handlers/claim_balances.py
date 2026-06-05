class ClaimBalancesHandler:
    def __init__(self, read_model, serializer):
        self.read_model = read_model
        self.serializer = serializer

    def get_claim_balances(self, **kwargs):
        payload = self.read_model.get_claim_balances(**kwargs)
        return self.serializer.serialize_claim_balances(payload)
