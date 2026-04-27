from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from etl.contracts import (
    EditorialBlip,
    EditorialExclusion,
    LaneEditorialDecision,
    LaneEditorialInput,
)
from etl.editorial_llm.client import request_lane_decision
from etl.editorial_llm.prompts import build_lane_prompt
from etl.signals.scoring import market_score


def parse_lane_decision(payload: dict[str, Any]) -> LaneEditorialDecision:
    normalized = _normalize_lane_decision_payload(payload)
    return LaneEditorialDecision.model_validate(normalized)


def parse_lane_decision_json(payload: str) -> LaneEditorialDecision:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid lane decision JSON") from exc
    return parse_lane_decision(parsed)


def decide_lane(lane_input: LaneEditorialInput, max_items: int = 6) -> LaneEditorialDecision:
    llm_decision = _try_llm_lane_decision(lane_input, max_items=max_items)
    if llm_decision is not None:
        return _enrich_lane_decision(llm_decision, lane_input)
    return _heuristic_lane_decision(lane_input, max_items=max_items)


def _try_llm_lane_decision(lane_input: LaneEditorialInput, max_items: int) -> LaneEditorialDecision | None:
    return request_lane_decision(
        lane_input=lane_input,
        prompt=build_lane_prompt(lane_input, max_items=max_items),
        parser=parse_lane_decision_json,
    )


def _normalize_lane_decision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    lane = str(payload.get("lane", "")).strip().lower()
    normalized = dict(payload)
    normalized["lane"] = lane
    normalized["included"] = [
        _normalize_included_item(item, lane)
        for item in payload.get("included", [])
        if isinstance(item, dict)
    ]
    normalized["excluded"] = [
        _normalize_excluded_item(item, lane)
        for item in payload.get("excluded", [])
        if isinstance(item, dict)
    ]
    return normalized


def _normalize_included_item(item: dict[str, Any], lane: str) -> dict[str, Any]:
    normalized = dict(item)
    name = str(normalized.get("name", "")).strip() or "Unknown"
    normalized.setdefault("id", _slugify(name))
    normalized.setdefault("quadrant", lane)
    normalized.setdefault("updatedAt", datetime.now(timezone.utc).isoformat())
    normalized["ring"] = _normalize_ring_value(normalized.get("ring"))
    normalized["trend"] = _normalize_trend_value(normalized.get("trend"))
    normalized["confidence"] = _normalize_confidence_value(normalized.get("confidence"))
    normalized.setdefault("description", name)
    normalized.setdefault("whyThisRing", "Included after lane editorial review.")
    normalized.setdefault("whyNow", "Relevant for the current radar cycle.")
    normalized.setdefault("useCases", [])
    normalized.setdefault("avoidWhen", [])
    normalized.setdefault("alternatives", [])
    normalized.setdefault("moved", 0)
    return normalized


def _normalize_excluded_item(item: dict[str, Any], lane: str) -> dict[str, Any]:
    normalized = dict(item)
    name = str(normalized.get("name", "")).strip() or "Unknown"
    normalized.setdefault("id", _slugify(name))
    normalized.setdefault("lane", lane)
    normalized.setdefault("reason", "Excluded after lane editorial review.")
    normalized.setdefault("marketScore", 0.0)
    return normalized


def _normalize_ring_value(value: Any) -> str:
    mapping = {
        "adopt": "adopt",
        "trial": "trial",
        "assess": "assess",
        "hold": "hold",
        "adoption": "adopt",
        "recommended": "adopt",
        "watch": "assess",
    }
    key = str(value or "assess").strip().lower()
    return mapping.get(key, "assess")


def _normalize_trend_value(value: Any) -> str:
    mapping = {
        "up": "up",
        "rising": "up",
        "increasing": "up",
        "down": "down",
        "falling": "down",
        "declining": "down",
        "stable": "stable",
        "steady": "stable",
        "flat": "stable",
        "new": "new",
        "emerging": "new",
    }
    key = str(value or "stable").strip().lower()
    return mapping.get(key, "stable")


def _normalize_confidence_value(value: Any) -> float:
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > 1.0:
            numeric = numeric / 100.0
        return max(0.0, min(1.0, numeric))

    mapping = {
        "very high": 0.95,
        "high": 0.9,
        "medium": 0.75,
        "moderate": 0.75,
        "low": 0.55,
    }
    key = str(value or "").strip().lower()
    return mapping.get(key, 0.7)


def _slugify(value: str) -> str:
    return "-".join(part for part in value.lower().replace("/", " ").split() if part)


def _enrich_lane_decision(decision: LaneEditorialDecision, lane_input: LaneEditorialInput) -> LaneEditorialDecision:
    candidates_by_id = {entity.canonical_slug: entity for entity in lane_input.candidates}
    candidates_by_name = {entity.canonical_name.strip().lower(): entity for entity in lane_input.candidates}

    for blip in decision.included:
        entity = candidates_by_id.get(blip.id) or candidates_by_name.get(blip.name.strip().lower())
        if entity is None:
            continue
        score = market_score(entity)
        blip.id = entity.canonical_slug
        blip.name = entity.canonical_name
        blip.quadrant = lane_input.lane
        blip.ring = _ring_for_score(score)
        blip.confidence = round(min(0.99, 0.45 + (score / 200.0)), 2)
        blip.marketScore = score
        blip.whyThisRing = _why_this_ring(score, lane_input.lane)
        blip.entityType = entity.editorial_kind
        blip.canonicalId = entity.canonical_slug
        blip.sourceCoverage = len({item.get("source") for item in entity.source_evidence})
        blip.signals = _public_signals(entity)
        blip.sourceFreshness = {"freshestDays": 1, "stalestDays": 30}
        blip.evidenceSummary = _evidence_summary(entity)
        blip.evidence = _public_evidence(entity)
        blip.alternatives = lane_input.nearby_alternatives.get(entity.canonical_slug, blip.alternatives)

    for excluded in decision.excluded:
        entity = candidates_by_id.get(excluded.id) or candidates_by_name.get(excluded.name.strip().lower())
        if entity is None:
            continue
        excluded.id = entity.canonical_slug
        excluded.name = entity.canonical_name
        excluded.lane = lane_input.lane
        excluded.marketScore = market_score(entity)

    return decision


def _heuristic_lane_decision(lane_input: LaneEditorialInput, max_items: int = 6) -> LaneEditorialDecision:
    ranked = sorted(lane_input.candidates, key=market_score, reverse=True)
    included: list[EditorialBlip] = []
    excluded: list[EditorialExclusion] = []
    now = datetime.now(timezone.utc).isoformat()

    for index, entity in enumerate(ranked):
        score = market_score(entity)
        if index < max_items:
            included.append(
                EditorialBlip(
                    id=entity.canonical_slug,
                    name=entity.canonical_name,
                    quadrant=lane_input.lane,
                    ring=_ring_for_score(score),
                    description=entity.description or f"{entity.canonical_name} in the {lane_input.lane} lane.",
                    trend=_trend_for_entity(entity),
                    confidence=round(min(0.99, 0.45 + (score / 200.0)), 2),
                    updatedAt=now,
                    marketScore=score,
                    whyThisRing=_why_this_ring(score, lane_input.lane),
                    whyNow=_why_now(entity),
                    useCases=_use_cases(entity),
                    avoidWhen=_avoid_when(entity),
                    alternatives=lane_input.nearby_alternatives.get(entity.canonical_slug, []),
                    entityType=entity.editorial_kind,
                    canonicalId=entity.canonical_slug,
                    sourceCoverage=len({item.get("source") for item in entity.source_evidence}),
                    signals=_public_signals(entity),
                    sourceFreshness={"freshestDays": 1, "stalestDays": 30},
                    evidenceSummary=_evidence_summary(entity),
                    evidence=_public_evidence(entity),
                )
            )
        else:
            excluded.append(
                EditorialExclusion(
                    id=entity.canonical_slug,
                    name=entity.canonical_name,
                    reason="Below the lane cut after comparing score, breadth, and redundancy.",
                    lane=lane_input.lane,
                    marketScore=score,
                )
            )

    return LaneEditorialDecision(lane=lane_input.lane, included=included, excluded=excluded, merge_notes=[])


def _public_signals(entity) -> dict[str, float]:
    return {
        "adoption": entity.adoption_signals.get("adoption", 0.0),
        "momentum": entity.momentum_signals.get("momentum", 0.0),
        "maturity": entity.maturity_signals.get("maturity", 0.0),
        "risk": entity.risk_signals.get("risk", 0.0),
    }


def _evidence_summary(entity) -> dict[str, Any]:
    return {
        "sources": sorted({str(item.get("source", "")) for item in entity.source_evidence if item.get("source")}),
        "metrics": sorted({str(item.get("metric", "")) for item in entity.source_evidence if item.get("metric")}),
        "hasExternalAdoption": len(entity.source_evidence) > 1,
        "githubOnly": {item.get("source") for item in entity.source_evidence} == {"github_trending"},
    }


def _public_evidence(entity) -> list[str]:
    return [
        f"{item.get('source', 'unknown')}:{item.get('metric', 'signal')}"
        for item in entity.source_evidence
    ]


def _ring_for_score(score: float) -> str:
    if score >= 78:
        return "adopt"
    if score >= 64:
        return "trial"
    if score >= 50:
        return "assess"
    return "hold"


def _trend_for_entity(entity) -> str:
    momentum = entity.momentum_signals.get("momentum", 0.0)
    adoption = entity.adoption_signals.get("adoption", 0.0)
    if momentum >= 80:
        return "up"
    if adoption < 45:
        return "new"
    return "stable"


def _why_this_ring(score: float, lane: str) -> str:
    ring = _ring_for_score(score)
    return f"{ring.title()} in {lane} because the combined market score is {score:.1f} with clear editorial relevance."


def _why_now(entity) -> str:
    if entity.momentum_signals.get("momentum", 0.0) >= 80:
        return "Current market chatter and ecosystem pull keep this unusually visible this cycle."
    return "It remains strategically relevant this quarter because teams keep building around it."


def _use_cases(entity) -> list[str]:
    family = entity.topic_family
    if family == "testing":
        return ["Delivery safety", "Regression control"]
    if family in {"ai", "ai-devex"}:
        return ["AI delivery workflows", "Developer enablement"]
    if entity.editorial_kind == "platform":
        return ["Platform standardization", "Operational consolidation"]
    return ["Core product delivery", "Team standardization"]


def _avoid_when(entity) -> list[str]:
    if entity.editorial_kind == "technique":
        return ["The team has not aligned on operating model changes"]
    return ["You need a radically different constraint profile than its mainstream fit"]
