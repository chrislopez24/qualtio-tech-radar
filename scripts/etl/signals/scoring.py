from __future__ import annotations

from statistics import mean, pvariance

from etl.contracts import MarketEntity

VALIDATION_ADOPTION_METRICS = {"reverse_dependents"}
VALIDATION_HEALTH_METRICS = {"default_version"}
VALIDATION_RISK_METRICS = {"known_vulnerabilities"}


def score_entity(entity: MarketEntity) -> MarketEntity:
    legacy_values = [
        float(item.get("normalized_value", 0.0) or 0.0)
        for item in entity.source_evidence
        if str(item.get("metric", "")) not in VALIDATION_ADOPTION_METRICS | VALIDATION_HEALTH_METRICS | VALIDATION_RISK_METRICS
    ]
    validation_adoption = _metric_values(entity, VALIDATION_ADOPTION_METRICS)
    validation_health = _metric_values(entity, VALIDATION_HEALTH_METRICS)
    validation_risk = _metric_values(entity, VALIDATION_RISK_METRICS)

    legacy_average = mean(legacy_values) if legacy_values else 0.0
    legacy_peak = max(legacy_values) if legacy_values else 0.0

    reverse_dependents = max(validation_adoption) if validation_adoption else 0.0
    default_version_present = 100.0 if validation_health else 0.0
    vulnerability_pressure = max(validation_risk) if validation_risk else 0.0

    adoption = legacy_average
    if reverse_dependents > 0.0:
        adoption = max(adoption, legacy_average + min(6.0, reverse_dependents / 25.0))

    momentum = max(legacy_peak, reverse_dependents * 0.85 if reverse_dependents > 0.0 else 0.0)
    breadth = min(100.0, float(len(set([*entity.implementation_languages, *entity.ecosystems])) * 18))
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
        "adoption": round(adoption, 2),
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
    }
    return entity


def market_score(entity: MarketEntity) -> float:
    adoption = entity.adoption_signals.get("adoption", 0.0)
    momentum = entity.momentum_signals.get("momentum", 0.0)
    maturity = entity.maturity_signals.get("maturity", 0.0)
    risk = entity.risk_signals.get("risk", 0.0)
    return round((adoption * 0.35) + (momentum * 0.30) + (maturity * 0.25) + ((100.0 - risk) * 0.10), 2)


def _metric_values(entity: MarketEntity, metrics: set[str]) -> list[float]:
    return [
        float(item.get("normalized_value", 0.0) or 0.0)
        for item in entity.source_evidence
        if str(item.get("metric", "")) in metrics
    ]
