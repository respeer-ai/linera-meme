class TransactionWatermarksQueryRepository:
    def __init__(self, db):
        self.db = db

    def get_latest_transaction_watermarks(self) -> dict:
        self.db.ensure_fresh_read_connection()
        self.db.cursor_dict.execute(
            '''
                SELECT
                    p.pool_id,
                    CONCAT(st.pool_chain_id, ':', st.pool_application_id) AS pool_application,
                    st.trade_time_ms AS created_at,
                    st.transaction_id,
                    CASE
                        WHEN st.side = 'buy_token_0' THEN 0
                        ELSE 1
                    END AS token_reversed
                FROM settled_trades st
                JOIN pools p
                  ON p.pool_application = CONCAT(st.pool_chain_id, ':', st.pool_application_id)
                JOIN (
                    SELECT
                        CONCAT(pool_chain_id, ':', pool_application_id) AS pool_application,
                        MAX(trade_time_ms) AS max_created_at
                    FROM settled_trades
                    GROUP BY CONCAT(pool_chain_id, ':', pool_application_id)
                ) latest
                  ON latest.pool_application = CONCAT(st.pool_chain_id, ':', st.pool_application_id)
                 AND latest.max_created_at = st.trade_time_ms
                ORDER BY
                    p.pool_id ASC,
                    st.trade_time_ms DESC,
                    st.transaction_id DESC,
                    token_reversed DESC
            '''
        )
        watermarks = {}
        for row in self.db.cursor_dict.fetchall() or []:
            pool_id = int(row['pool_id'])
            pool_application = str(row['pool_application'])
            chain_id, owner = pool_application.split(':', 1)
            key = (pool_id, chain_id, owner)
            if key in watermarks:
                continue
            watermarks[key] = (
                int(row['created_at']),
                int(row['transaction_id']),
                1 if bool(row['token_reversed']) else 0,
            )
        return watermarks
