from dataclasses import dataclass


@dataclass
class EvidenceRecord:
    source: str
    metric: str
    subject_id: str
    raw_value: float | int | str
    normalized_value: float
    observed_at: str
    freshness_days: int
