from __future__ import annotations

from statistics import mean, pvariance

from etl.contracts import MarketEntity

VALIDATION_ADOPTION_METRICS = {"reverse_dependents"}
VALIDATION_HEALTH_METRICS = {"default_version"}
VALIDATION_RISK_METRICS = {"known_vulnerabilities"}
VALIDATION_METRICS = VALIDATION_ADOPTION_METRICS | VALIDATION_HEALTH_METRICS | VALIDATION_RISK_METRICS
UNCORROBORATED_ADOPTION_FACTOR = 0.63
UNCORROBORATED_MOMENTUM_FACTOR = 0.565
DISCUSSION_SOURCES = {"hackernews"}
DISCUSSION_ONLY_SIGNAL_FACTOR = 0.70
VULNERABILITY_PENALTY_THRESHOLD = 60.0
VULNERABILITY_PENALTY_FACTOR = 0.56
ANCHOR_MATURITY_TARGET = 95.0
VALIDATED_NICHE_MATURITY_FLOOR = 75.0


def score_entity(entity: MarketEntity) -> MarketEntity:
    legacy_evidence = [
        item
        for item in entity.source_evidence
        if str(item.get("metric", "")) not in VALIDATION_METRICS
    ]
    legacy_values = [
        float(item.get("normalized_value", 0.0) or 0.0)
        for item in legacy_evidence
    ]
    validation_adoption = _metric_values(entity, VALIDATION_ADOPTION_METRICS)
    validation_health = _metric_values(entity, VALIDATION_HEALTH_METRICS)
    validation_risk = _metric_values(entity, VALIDATION_RISK_METRICS)

    legacy_average = mean(legacy_values) if legacy_values else 0.0
    legacy_peak = max(legacy_values) if legacy_values else 0.0

    reverse_dependents = max(validation_adoption) if validation_adoption else 0.0
    default_version_present = 100.0 if validation_health else 0.0
    vulnerability_pressure = max(validation_risk) if validation_risk else 0.0
    legacy_sources = {str(item.get("source", "")).strip() for item in legacy_evidence if item.get("source")}
    legacy_source_count = len(legacy_sources) if legacy_sources else len(legacy_values)
    implementation_scope_count = len(set([*entity.implementation_languages, *entity.ecosystems]))
    has_validation = reverse_dependents > 0.0 or default_version_present > 0.0
    is_uncorroborated = bool(legacy_values) and legacy_source_count <= 1 and not has_validation
    is_discussion_only = (
        is_uncorroborated
        and implementation_scope_count == 0
        and legacy_sources <= DISCUSSION_SOURCES
    )

    adoption = legacy_average
    if is_uncorroborated:
        adoption *= UNCORROBORATED_ADOPTION_FACTOR
    if is_discussion_only:
        adoption *= DISCUSSION_ONLY_SIGNAL_FACTOR
    if reverse_dependents > 0.0:
        adoption = max(adoption, legacy_average + min(6.0, reverse_dependents / 25.0))

    corroborated_peak = legacy_peak
    if is_uncorroborated:
        corroborated_peak *= UNCORROBORATED_MOMENTUM_FACTOR
    if is_discussion_only:
        corroborated_peak *= DISCUSSION_ONLY_SIGNAL_FACTOR
    momentum = max(corroborated_peak, reverse_dependents * 0.85 if reverse_dependents > 0.0 else 0.0)
    breadth = min(100.0, float(implementation_scope_count * 18))
    maturity = min(
        100.0,
        45.0
        + float(len(legacy_values) * 10)
        + breadth * 0.2
        + (10.0 if default_version_present > 0.0 else 0.0)
        + min(6.0, reverse_dependents / 20.0),
    )
    variance = pvariance(legacy_values) if len(legacy_values) > 1 else 0.0
    stability = max(0.0, 100.0 - min(100.0, variance))
    base_risk = max(0.0, 35.0 - min(30.0, len(legacy_values) * 5.0))
    risk = min(100.0, base_risk + (vulnerability_pressure * 0.6))

    entity.adoption_signals = {
        "adoption": round(min(100.0, adoption), 2),
        "breadth": round(breadth, 2),
    }
    entity.momentum_signals = {
        "momentum": round(momentum, 2),
        "stability": round(stability, 2),
    }
    entity.maturity_signals = {
        "maturity": round(maturity, 2),
    }
    entity.risk_signals = {
        "risk": round(risk, 2),
        "vulnerability_pressure": round(vulnerability_pressure, 2),
    }
    return entity


def market_score(entity: MarketEntity) -> float:
    adoption = entity.adoption_signals.get("adoption", 0.0)
    breadth = entity.adoption_signals.get("breadth", 0.0)
    momentum = entity.momentum_signals.get("momentum", 0.0)
    maturity = entity.maturity_signals.get("maturity", 0.0)
    risk = entity.risk_signals.get("risk", 0.0)
    vulnerability_pressure = entity.risk_signals.get("vulnerability_pressure", 0.0)
    vulnerability_penalty = (
        max(0.0, vulnerability_pressure - VULNERABILITY_PENALTY_THRESHOLD)
        * VULNERABILITY_PENALTY_FACTOR
    )
    has_validation = any(str(item.get("metric", "")) in VALIDATION_METRICS for item in entity.source_evidence)
    broad_validated_bonus = 0.0
    if has_validation and maturity >= 80.0 and momentum <= 80.0 and breadth >= 60.0:
        broad_validated_bonus = min(8.0, (breadth - 60.0) * 0.27)
    anchor_maturity_bonus = 0.0
    if has_validation and adoption >= 85.0 and momentum >= 85.0 and 85.0 <= maturity < ANCHOR_MATURITY_TARGET:
        anchor_maturity_bonus = min(2.5, (ANCHOR_MATURITY_TARGET - maturity) * 0.5)
    niche_validation_bonus = 0.0
    if (
        has_validation
        and vulnerability_pressure <= 20.0
        and breadth <= 45.0
        and 45.0 <= momentum <= 65.0
        and VALIDATED_NICHE_MATURITY_FLOOR <= maturity < 85.0
    ):
        niche_validation_bonus = min(2.0, (maturity - VALIDATED_NICHE_MATURITY_FLOOR) * 0.2)
    return round(
        (adoption * 0.35)
        + (momentum * 0.30)
        + (maturity * 0.25)
        + ((100.0 - risk) * 0.10)
        + broad_validated_bonus
        + anchor_maturity_bonus
        + niche_validation_bonus
        - vulnerability_penalty,
        2,
    )


def _metric_values(entity: MarketEntity, metrics: set[str]) -> list[float]:
    return [
        float(item.get("normalized_value", 0.0) or 0.0)
        for item in entity.source_evidence
        if str(item.get("metric", "")) in metrics
    ]
