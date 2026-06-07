class BusinessFreshnessReadModel:
    def __init__(
        self,
        *,
        raw_repository,
        processing_cursor_repository,
        settled_trade_projection_repository,
        clock_ms=None,
    ):
        self.raw_repository = raw_repository
        self.processing_cursor_repository = processing_cursor_repository
        self.settled_trade_projection_repository = settled_trade_projection_repository
        self.clock_ms = clock_ms or (lambda: None)

    def load_snapshot(self, *, chain_id: str | None = None, pool_application: str | None = None) -> dict:
        l1 = self._load_l1(chain_id)
        cursors = self.processing_cursor_repository.list_cursors(limit=200)
        l2 = self._find_cursor(cursors, 'layer2_normalizer')
        l3 = self._find_cursor(cursors, 'layer3_market_deriver')
        product_watermark_ms = self._load_product_watermark(pool_application)

        status, reason_codes = self._classify(
            chain_id=chain_id,
            pool_application=pool_application,
            l1=l1,
            l2=l2,
            l3=l3,
            product_watermark_ms=product_watermark_ms,
        )
        return {
            'scope': {'chain_id': chain_id, 'pool_application': pool_application},
            'status': status,
            'reason_codes': reason_codes,
            'watermarks': {
                'l1': l1,
                'l2': l2,
                'l3': l3,
                'product': {'market_watermark_ms': product_watermark_ms},
            },
            'checked_at_ms': self.clock_ms(),
        }

    def _load_l1(self, chain_id: str | None) -> dict | None:
        if chain_id is None:
            return None
        rows = self.raw_repository.list_chain_cursors(chain_ids=(chain_id,), limit=1)
        return rows[0] if rows else None

    def _load_product_watermark(self, pool_application: str | None) -> int | None:
        if pool_application is None:
            return None
        return self.settled_trade_projection_repository.load_pool_market_watermark_ms(pool_application)

    def _classify(
        self,
        *,
        chain_id: str | None,
        pool_application: str | None,
        l1: dict | None,
        l2: dict | None,
        l3: dict | None,
        product_watermark_ms: int | None,
    ) -> tuple[str, list[str]]:
        if chain_id is None:
            return 'unknown', ['chain_id_missing']
        if l1 is None:
            return 'l1_unavailable', ['l1_cursor_missing']
        l1_height = self._int_or_none(l1.get('last_finalized_height'))
        l2_sequence = self._int_or_none(l2.get('last_sequence') if l2 else None)
        if l1_height is not None and (l2_sequence is None or l2_sequence < l1_height):
            return 'normalization_stale', ['l2_behind_l1']
        l3_sequence = self._int_or_none(l3.get('last_sequence') if l3 else None)
        if l2_sequence is not None and (l3_sequence is None or l3_sequence < l2_sequence):
            return 'market_derivation_stale', ['l3_behind_l2']
        if pool_application is not None and product_watermark_ms is None:
            return 'product_read_stale', ['product_watermark_missing']
        return 'fresh', []

    def _find_cursor(self, cursors: list[dict], cursor_name: str) -> dict | None:
        for cursor in cursors:
            if cursor.get('cursor_name') == cursor_name:
                return cursor
        return None

    def _int_or_none(self, value) -> int | None:
        if value is None:
            return None
        return int(value)
