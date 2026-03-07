from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from etl.evidence import EvidenceRecord


@dataclass(frozen=True)
class EvidenceScoreSummary:
    adoption: float
    mindshare: float
    health: float
    risk: float
    composite: float
    source_coverage: int
    has_external_adoption: bool
    github_only: bool


ADOPTION_METRICS = {"reverse_dependents", "downloads_last_month"}
MINDSHARE_METRICS = {"tag_activity"}
HEALTH_METRICS = {"default_version"}
RISK_METRICS = {"known_vulnerabilities"}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _metric_max(evidence: Sequence[EvidenceRecord], metrics: set[str]) -> float:
    values = [
        float(record.normalized_value)
        for record in evidence
        if record.metric in metrics
    ]
    if not values:
        return 0.0
    return _clamp(max(values))


def _source_families(signals: Mapping[str, float], evidence: Sequence[EvidenceRecord]) -> set[str]:
    families: set[str] = set()

    if float(signals.get("gh_momentum", 0.0) or 0.0) > 0.0 or float(signals.get("gh_popularity", 0.0) or 0.0) > 0.0:
        families.add("github")
    if float(signals.get("hn_heat", 0.0) or 0.0) > 0.0:
        families.add("hackernews")

    for record in evidence:
        source = str(record.source or "").strip().lower()
        if source:
            families.add(source)

    return families


def score_evidence(
    *,
    signals: Mapping[str, float],
    evidence: Sequence[EvidenceRecord],
    github_stars: float = 0.0,
    github_forks: float = 0.0,
) -> EvidenceScoreSummary:
    gh_momentum = _clamp(float(signals.get("gh_momentum", 0.0) or 0.0))
    gh_popularity = _clamp(float(signals.get("gh_popularity", 0.0) or 0.0))
    hn_heat = _clamp(float(signals.get("hn_heat", 0.0) or 0.0))

    families = _source_families(signals, evidence)
    source_coverage = len(families)
    github_only = families == {"github"}

    external_adoption = _metric_max(evidence, ADOPTION_METRICS)
    tag_activity = _metric_max(evidence, MINDSHARE_METRICS)
    version_presence = _metric_max(evidence, HEALTH_METRICS)
    vulnerability_pressure = _metric_max(evidence, RISK_METRICS)

    github_adoption = _clamp((gh_popularity * 0.55) + (gh_momentum * 0.45))
    if external_adoption > 0.0:
        adoption = _clamp((external_adoption * 0.7) + (github_adoption * 0.3))
    else:
        adoption = _clamp(github_adoption * 0.85)

    mindshare = _clamp(max(hn_heat, tag_activity))

    corroborating_coverage = len({family for family in families if family != "osv"})
    coverage_bonus = min(15.0, max(0, corroborating_coverage - 1) * 5.0)
    repo_scale_bonus = min(10.0, ((max(github_stars, 0.0) / 250000.0) * 7.0) + ((max(github_forks, 0.0) / 50000.0) * 3.0))
    health = _clamp((gh_momentum * 0.6) + (gh_popularity * 0.15) + (version_presence * 0.1) + coverage_bonus + repo_scale_bonus)

    if vulnerability_pressure > 0.0:
        risk = _clamp(100.0 - vulnerability_pressure)
    else:
        risk = 70.0

    composite = (adoption * 0.45) + (mindshare * 0.20) + (health * 0.20) + (risk * 0.15)

    if github_only:
        composite -= 7.0
    elif source_coverage == 1:
        composite -= 5.0
    elif source_coverage >= 3:
        composite += 4.0

    if external_adoption > 0.0:
        composite += min(6.0, external_adoption / 20.0)

    return EvidenceScoreSummary(
        adoption=round(_clamp(adoption), 2),
        mindshare=round(_clamp(mindshare), 2),
        health=round(_clamp(health), 2),
        risk=round(_clamp(risk), 2),
        composite=round(_clamp(composite), 2),
        source_coverage=source_coverage,
        has_external_adoption=external_adoption > 0.0,
        github_only=github_only,
    )
