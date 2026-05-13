class ProjectionQueryUnavailableError(RuntimeError):
    def __init__(self, query_name: str):
        super().__init__(f'Projection query unavailable: {query_name}')
        self.query_name = query_name
