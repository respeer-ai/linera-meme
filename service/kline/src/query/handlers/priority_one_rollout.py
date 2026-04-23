import json
import os


class PriorityOneRollout:
    def __init__(self, db):
        self.db = db

    def mode(self) -> str:
        return os.getenv('KLINE_PRIORITY1_ROLLOUT_MODE', 'new').strip().lower() or 'new'

    def use_legacy(self) -> bool:
        return self.mode() == 'legacy'

    def parity_enabled(self) -> bool:
        value = os.getenv('KLINE_PRIORITY1_PARITY', '0').strip().lower()
        return value in {'1', 'true', 'yes', 'on'}

    def compare(
        self,
        *,
        endpoint: str,
        legacy_payload,
        new_payload,
        owner: str | None = None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        status: str | None = None,
    ) -> None:
        if not self.parity_enabled():
            return
        if self._to_json(legacy_payload) == self._to_json(new_payload):
            return
        print(
            f'Priority-1 parity mismatch endpoint={endpoint} '
            f'pool_application={pool_application} pool_id={pool_id} owner={owner} status={status}'
        )
        self._record_mismatch(
            endpoint=endpoint,
            legacy_payload=legacy_payload,
            new_payload=new_payload,
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
            status=status,
        )

    def _record_mismatch(
        self,
        *,
        endpoint: str,
        legacy_payload,
        new_payload,
        owner: str | None = None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        status: str | None = None,
    ) -> None:
        if self.db is None or not hasattr(self.db, 'record_diagnostic_event'):
            return
        self.db.record_diagnostic_event(
            source='phase1_parity',
            event_type='priority1_mismatch',
            severity='warning',
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
            status=status,
            details={
                'endpoint': endpoint,
                'legacy_payload': legacy_payload,
                'new_payload': new_payload,
                'rollout_mode': self.mode(),
            },
        )

    def _to_json(self, payload) -> str:
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
