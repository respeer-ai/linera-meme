from storage.mysql.pool_catalog_projection_repo import PoolCatalogProjectionRepository
from storage.mysql.pool_metadata_projection_resolver import PoolMetadataProjectionResolver
from storage.mysql.pool_state_projection_repo import PoolStateProjectionRepository
from account_codec import AccountCodec


class TransactionWatermarksQueryRepository:
    def __init__(self, db, *, metadata_resolver=None):
        self.db = db
        self.metadata_resolver = (
            metadata_resolver
            or PoolMetadataProjectionResolver(
                pool_catalog_projection_repository=PoolCatalogProjectionRepository(
                    getattr(db, 'connection', db)
                ),
                pool_state_projection_repository=PoolStateProjectionRepository(db),
            )
        )
        self.account_codec = AccountCodec()

    def _pool_application_expr(self, alias: str) -> str:
        return f"{alias}.pool_application_id"

    def get_latest_transaction_watermarks(self) -> dict:
        self.db.ensure_fresh_read_connection()
        try:
            self.db.cursor_dict.execute(
                f'''
                    SELECT
                        {self._pool_application_expr('st')} AS pool_application,
                        st.trade_time_ms AS created_at,
                        st.transaction_id,
                        CASE
                            WHEN st.side = 'buy_token_0' THEN 0
                            ELSE 1
                        END AS token_reversed
                    FROM settled_trades st
                    JOIN (
                        SELECT
                            pool_chain_id,
                            pool_application_id,
                            MAX(trade_time_ms) AS max_created_at
                        FROM settled_trades
                        GROUP BY pool_chain_id, pool_application_id
                    ) latest
                      ON latest.pool_chain_id = st.pool_chain_id
                     AND latest.pool_application_id = st.pool_application_id
                     AND latest.max_created_at = st.trade_time_ms
                    ORDER BY
                        pool_application ASC,
                        st.trade_time_ms DESC,
                        st.transaction_id DESC,
                        token_reversed DESC
                '''
            )
        except Exception as exc:
            error_code = getattr(exc, 'errno', None)
            error_text = str(exc)
            if error_code == 1146 and 'settled_trades' in error_text:
                return {}
            raise
        rows = list(self.db.cursor_dict.fetchall() or [])
        metadata_by_pool_application = self.metadata_resolver.metadata_by_pool_application()
        watermarks = {}
        for row in rows:
            pool_application = str(row['pool_application'])
            metadata = metadata_by_pool_application.get(pool_application)
            if metadata is None:
                continue
            if metadata.get('pool_id') is None:
                continue
            pool_id = int(metadata['pool_id'])
            parsed_pool_application = self.account_codec.parse_account(pool_application)
            chain_id = parsed_pool_application['chain_id']
            owner = parsed_pool_application['owner']
            key = (pool_id, chain_id, owner)
            if key in watermarks:
                continue
            watermarks[key] = (
                int(row['created_at']),
                int(row['transaction_id']),
                1 if bool(row['token_reversed']) else 0,
            )
        return watermarks
