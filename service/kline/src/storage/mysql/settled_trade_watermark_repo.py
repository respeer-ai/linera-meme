from storage.mysql.repository_connection_mixin import MysqlRepositoryConnectionMixin


class SettledTradeWatermarkRepository(MysqlRepositoryConnectionMixin):
    def __init__(self, connection):
        self.connection = connection
        self.settled_trades_table = 'settled_trades'

    def load_pool_market_watermark_ms(self, pool_application: str) -> int | None:
        cursor = self.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT MAX(trade_time_ms) AS market_watermark_ms
                FROM {self.settled_trades_table}
                WHERE pool_application_id = %s
                ''',
                (pool_application,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            watermark = row.get('market_watermark_ms') if isinstance(row, dict) else row[0]
            if watermark is None:
                return None
            return int(watermark)
        finally:
            cursor.close()
