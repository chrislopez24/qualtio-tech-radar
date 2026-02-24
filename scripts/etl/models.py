from dataclasses import dataclass
from typing import Optional


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