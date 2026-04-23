class PositionsHandler:
    def __init__(self, read_model, serializer):
        self.read_model = read_model
        self.serializer = serializer

    def get_positions(self, **kwargs):
        payload = self.read_model.get_positions(**kwargs)
        return self.serializer.serialize_positions(payload)
