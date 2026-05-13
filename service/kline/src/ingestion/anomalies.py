from dataclasses import dataclass


@dataclass(slots=True)
class IngestionAnomaly:
    anomaly_type: str
    object_identity: str
    details: dict[str, object] | None = None

