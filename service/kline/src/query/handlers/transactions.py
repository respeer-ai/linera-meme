class TransactionsHandler:
    def __init__(self, read_model, serializer):
        self.read_model = read_model
        self.serializer = serializer

    def get_transactions(self, **kwargs):
        payload = self.read_model.get_transactions(**kwargs)
        return self.serializer.serialize_transactions(payload)

    def get_information(self, **kwargs):
        payload = self.read_model.get_information(**kwargs)
        return self.serializer.serialize_information(payload)
