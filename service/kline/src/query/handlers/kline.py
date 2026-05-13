class KlineHandler:
    def __init__(self, read_model, serializer):
        self.read_model = read_model
        self.serializer = serializer

    def get_points(self, **kwargs):
        payload = self.read_model.get_points(**kwargs)
        return self.serializer.serialize_points(payload)

    def get_information(self, **kwargs):
        payload = self.read_model.get_information(**kwargs)
        return self.serializer.serialize_information(payload)
