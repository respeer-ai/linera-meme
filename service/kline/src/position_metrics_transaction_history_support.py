class PositionMetricsTransactionHistorySupport:
    def __init__(
        self,
        *,
        account_payload_to_string,
    ):
        self.account_payload_to_string = account_payload_to_string

    def normalize_live_transaction(self, tx: dict) -> dict:
        return {
            'transaction_id': tx.get('transactionId'),
            'transaction_type': tx.get('transactionType'),
            'from_account': self.account_payload_to_string(tx.get('from')),
            'amount_0_in': tx.get('amount0In'),
            'amount_0_out': tx.get('amount0Out'),
            'amount_1_in': tx.get('amount1In'),
            'amount_1_out': tx.get('amount1Out'),
            'liquidity': tx.get('liquidity'),
            'created_at': int(tx.get('createdAt') or 0),
        }

    def merge_transaction_history(
        self,
        persisted_history: list[dict] | None,
        live_history: list[dict] | None,
    ) -> list[dict]:
        merged: dict[tuple, dict] = {}

        for tx in persisted_history or []:
            merged[self._history_transaction_identity(tx)] = tx

        for tx in live_history or []:
            merged[self._history_transaction_identity(tx)] = tx

        return sorted(
            merged.values(),
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
            ),
        )

    def build_transaction_gap_summary(
        self,
        transaction_history: list[dict] | None,
        *,
        start_id: int | None = None,
        end_id: int | None = None,
        sample_limit: int = 8,
    ) -> dict:
        transaction_ids = sorted(
            {
                int(tx.get('transaction_id'))
                for tx in (transaction_history or [])
                if tx.get('transaction_id') is not None
            }
        )
        if not transaction_ids:
            return self._gap_summary(
                start_id=None,
                end_id=None,
                missing_count=0,
                missing_ids_sample=[],
            )

        lower_bound = transaction_ids[0] if start_id is None else max(int(start_id), transaction_ids[0])
        upper_bound = transaction_ids[-1] if end_id is None else min(int(end_id), transaction_ids[-1])
        if lower_bound > upper_bound:
            return self._gap_summary(
                start_id=lower_bound,
                end_id=upper_bound,
                missing_count=0,
                missing_ids_sample=[],
            )

        return self._gap_summary(
            start_id=lower_bound,
            end_id=upper_bound,
            missing_count=0,
            missing_ids_sample=[],
        )

    def _history_transaction_identity(self, tx: dict) -> tuple:
        return (
            int(tx.get('transaction_id') or 0),
            int(tx.get('created_at') or 0),
            tx.get('transaction_type'),
            tx.get('from_account'),
        )

    def _gap_summary(
        self,
        *,
        start_id,
        end_id,
        missing_count: int,
        missing_ids_sample: list[int],
    ) -> dict:
        return {
            'has_internal_gaps': False,
            'start_id': start_id,
            'end_id': end_id,
            'missing_count': missing_count,
            'missing_ids_sample': missing_ids_sample,
            'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
        }
