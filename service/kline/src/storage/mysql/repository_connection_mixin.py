class MysqlRepositoryConnectionMixin:
    def ensure_connection(self) -> None:
        self.connection.ping(reconnect=True, attempts=1, delay=0)

    def cursor(self, **kwargs):
        self.ensure_connection()
        return self.connection.cursor(**kwargs)
