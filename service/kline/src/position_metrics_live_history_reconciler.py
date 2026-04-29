class PositionMetricsLiveHistoryReconciler:
    def __init__(
        self,
        *,
        normalize_live_transaction,
        merge_transaction_history,
        build_transaction_gap_summary,
    ):
        self.normalize_live_transaction = normalize_live_transaction
        self.merge_transaction_history = merge_transaction_history
        self.build_transaction_gap_summary = build_transaction_gap_summary

    def reconcile(
        self,
        *,
        position: dict,
        payload_data: dict,
        liquidity_history: list[dict] | None = None,
        pool_transaction_history: list[dict] | None = None,
        pool_swap_count_since_open: int | None = None,
        pool_history_gap_summary: dict | None = None,
    ) -> dict:
        live_transactions = [
            self.normalize_live_transaction(tx)
            for tx in (payload_data.get('latestTransactions') or [])
        ]
        if not live_transactions:
            return {
                'liquidity_history': liquidity_history,
                'pool_transaction_history': pool_transaction_history,
                'pool_swap_count_since_open': pool_swap_count_since_open,
                'pool_history_gap_summary': pool_history_gap_summary,
            }

        pool_transaction_history = self.merge_transaction_history(
            pool_transaction_history,
            live_transactions,
        )
        pool_history_gap_summary = self.build_transaction_gap_summary(pool_transaction_history)
        liquidity_history = [
            tx
            for tx in (pool_transaction_history or [])
            if tx.get('from_account') == position['owner']
            and tx.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}
        ]
        if liquidity_history:
            latest_position_tx = max(
                liquidity_history,
                key=lambda row: (
                    int(row.get('created_at') or 0),
                    int(row.get('transaction_id') or 0),
                ),
            )
            pool_swap_count_since_open = sum(
                1
                for tx in (pool_transaction_history or [])
                if tx.get('transaction_type') in {'BuyToken0', 'SellToken0'}
                and (
                    int(tx.get('created_at') or 0),
                    int(tx.get('transaction_id') or 0),
                )
                >= (
                    int(latest_position_tx.get('created_at') or 0),
                    int(latest_position_tx.get('transaction_id') or 0),
                )
            )
        return {
            'liquidity_history': liquidity_history,
            'pool_transaction_history': pool_transaction_history,
            'pool_swap_count_since_open': pool_swap_count_since_open,
            'pool_history_gap_summary': pool_history_gap_summary,
        }
