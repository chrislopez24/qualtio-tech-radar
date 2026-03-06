from dataclasses import dataclass


@dataclass
class EvidenceRecord:
    """Record of evidence/metrics collected from various sources.

    This class stores a single piece of evidence about a technology,
    including the source, metric type, raw and normalized values,
    and freshness information.

    Attributes:
        source: Origin of the evidence (e.g., "deps_dev", "github", "hn")
        metric: Type of metric being recorded (e.g., "reverse_dependents", "stars")
        subject_id: Identifier of the subject (e.g., "npm:react", "github:facebook/react")
        raw_value: Original value from the source (can be float, int, or string)
        normalized_value: Value normalized to a 0-100 scale for comparison
        observed_at: ISO 8601 timestamp when the evidence was observed
        freshness_days: Number of days since the evidence was collected
    """
    source: str
    metric: str
    subject_id: str
    raw_value: float | int | str
    normalized_value: float
    observed_at: str
    freshness_days: int
