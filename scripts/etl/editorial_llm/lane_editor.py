from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from etl.contracts import (
    EditorialBlip,
    EditorialExclusion,
    LaneEditorialDecision,
    LaneEditorialInput,
)
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
    llm_decision = _try_llm_lane_decision(lane_input)
    if llm_decision is not None:
        return llm_decision
    return _heuristic_lane_decision(lane_input, max_items=max_items)


def resolve_llm_config() -> dict[str, str] | None:
    synthetic_api_key = os.environ.get("SYNTHETIC_API_KEY")
    if synthetic_api_key:
        return {
            "api_key": synthetic_api_key,
            "base_url": os.environ.get("SYNTHETIC_API_URL", "https://api.synthetic.new/v1"),
            "model": os.environ.get("SYNTHETIC_MODEL", "hf:MiniMaxAI/MiniMax-M2.5"),
        }

    return None


def _try_llm_lane_decision(lane_input: LaneEditorialInput) -> LaneEditorialDecision | None:
    try:
        from openai import OpenAI
    except Exception:  # pragma: no cover - optional runtime dependency path
        return None

    config = resolve_llm_config()
    if config is None:
        return None

    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )
    messages = [
        {"role": "system", "content": "You are an editor for a technology radar. Return strict JSON only."},
        {"role": "user", "content": build_lane_prompt(lane_input)},
    ]

    for _ in range(2):
        try:
            response = client.chat.completions.create(
                model=config["model"],
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception:
            continue

        content = response.choices[0].message.content if response.choices else None
        if not content:
            continue

        try:
            return parse_lane_decision_json(content)
        except ValueError:
            continue

    return None


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
        return float(value)

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
                    signals={
                        "adoption": entity.adoption_signals.get("adoption", 0.0),
                        "momentum": entity.momentum_signals.get("momentum", 0.0),
                        "maturity": entity.maturity_signals.get("maturity", 0.0),
                        "risk": entity.risk_signals.get("risk", 0.0),
                    },
                    sourceFreshness={"freshestDays": 1, "stalestDays": 30},
                    evidenceSummary={
                        "sources": sorted({str(item.get("source", "")) for item in entity.source_evidence if item.get("source")}),
                        "metrics": sorted({str(item.get("metric", "")) for item in entity.source_evidence if item.get("metric")}),
                        "hasExternalAdoption": len(entity.source_evidence) > 1,
                        "githubOnly": {item.get("source") for item in entity.source_evidence} == {"github_trending"},
                    },
                    evidence=[
                        f"{item.get('source', 'unknown')}:{item.get('metric', 'signal')}"
                        for item in entity.source_evidence
                    ],
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
