from __future__ import annotations

from statistics import mean, pvariance

from etl.contracts import MarketEntity


def score_entity(entity: MarketEntity) -> MarketEntity:
    values = [float(item.get("normalized_value", 0.0) or 0.0) for item in entity.source_evidence]
    adoption = mean(values) if values else 0.0
    momentum = max(values) if values else 0.0
    breadth = min(100.0, float(len(set([*entity.implementation_languages, *entity.ecosystems])) * 18))
    maturity = min(100.0, 45.0 + float(len(entity.source_evidence) * 10) + breadth * 0.2)
    variance = pvariance(values) if len(values) > 1 else 0.0
    stability = max(0.0, 100.0 - min(100.0, variance))
    risk = max(0.0, 35.0 - min(30.0, len(entity.source_evidence) * 5.0))

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
