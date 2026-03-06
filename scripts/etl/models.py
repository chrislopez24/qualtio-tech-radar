from dataclasses import dataclass, field
from typing import Optional, Dict, List

from etl.evidence import EvidenceRecord


@dataclass
class SourceTechnology:
    name: str
    source: str
    url: Optional[str] = None
    description: Optional[str] = None
    stars: Optional[int] = None
    trending_date: Optional[str] = None


@dataclass
class TechnologySignal:
    name: str
    source: str
    signal_type: str
    score: float
    raw_data: dict


@dataclass
class TechnologyClassification:
    name: str
    category: str
    quadrant: str
    ring: str
    description: str
    is_new: bool = False
    # Canonical entity fields for Radar V2
    canonical_id: Optional[str] = None
    entity_type: str = "technology"
    evidence: List[EvidenceRecord] = field(default_factory=list)


@dataclass
class TemporalAnalysis:
    trend: str
    activity_score: float
    recent_count: int = 0
    new_count: int = 0
    legacy_count: int = 0
    domain_breakdown: Optional[Dict[str, float]] = None