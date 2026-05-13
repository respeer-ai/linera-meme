class MysqlRepositoryConnectionMixin:
    def ensure_connection(self) -> None:
        ping = getattr(self.connection, 'ping', None)
        if callable(ping):
            ping(reconnect=True, attempts=1, delay=0)

    def cursor(self, **kwargs):
        self.ensure_connection()
        return self.connection.cursor(**kwargs)
