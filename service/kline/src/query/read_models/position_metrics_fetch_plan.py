from query.read_models.position_metrics_fetch_stage import PositionMetricsFetchStage
from query.read_models.position_metrics_fetch_reason_code import PositionMetricsFetchReasonCode


class PositionMetricsFetchPlan:
    def __init__(
        self,
        *,
        stage: str,
        fetch_reason_code: str,
        fast_path_payload=None,
        payload_result=None,
        needs_assembly: bool,
    ):
        self.stage = stage
        self.fetch_reason_code = fetch_reason_code
        self.fast_path_payload = fast_path_payload
        self.payload_result = payload_result
        self.needs_assembly = bool(needs_assembly)

    @property
    def projected_metrics(self):
        if self.payload_result is None:
            return None
        return self.payload_result.metrics

    def is_snapshot_fast_path(self) -> bool:
        return self.stage == PositionMetricsFetchStage.SNAPSHOT_FAST_PATH

    def is_payload_only(self) -> bool:
        return self.stage == PositionMetricsFetchStage.PAYLOAD_ONLY

    def needs_replay_fallback(self) -> bool:
        return self.stage == PositionMetricsFetchStage.REPLAY_FALLBACK

    def resolved_projected_metrics(self) -> dict | None:
        if self.fast_path_payload is not None:
            return self.fast_path_payload.get('projected_metrics', self.fast_path_payload)
        return self.projected_metrics

    def snapshot_shadow(self) -> dict | None:
        if self.fast_path_payload is None:
            return None
        return self.fast_path_payload.get('snapshot_shadow')

    def resolved_fetch_stage(self) -> str:
        if self.is_snapshot_fast_path():
            return PositionMetricsFetchStage.SNAPSHOT_FAST_PATH
        if self.is_payload_only():
            return PositionMetricsFetchStage.PAYLOAD_ONLY
        return PositionMetricsFetchStage.REPLAY_FALLBACK

    def resolved_fetch_reason_code(self) -> str:
        if self.is_snapshot_fast_path():
            return PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_HIT
        if self.is_payload_only():
            return PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_PAYLOAD_ONLY
        return PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_PAYLOAD_REQUIRES_HISTORY

    @classmethod
    def snapshot_fast_path(cls, payload: dict):
        return cls(
            stage=PositionMetricsFetchStage.SNAPSHOT_FAST_PATH,
            fetch_reason_code=PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_HIT,
            fast_path_payload=payload,
            needs_assembly=False,
        )

    @classmethod
    def payload_only(cls, payload_result):
        return cls(
            stage=PositionMetricsFetchStage.PAYLOAD_ONLY,
            fetch_reason_code=PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_PAYLOAD_ONLY,
            payload_result=payload_result,
            needs_assembly=False,
        )

    @classmethod
    def replay_fallback(cls, payload_result):
        return cls(
            stage=PositionMetricsFetchStage.REPLAY_FALLBACK,
            fetch_reason_code=PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_PAYLOAD_REQUIRES_HISTORY,
            payload_result=payload_result,
            needs_assembly=True,
        )
