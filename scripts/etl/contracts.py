from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


LaneName = Literal["languages", "frameworks", "tools", "platforms", "techniques"]
EditorialKind = Literal["language", "framework", "tool", "platform", "technique"]
RingName = Literal["adopt", "trial", "assess", "hold"]
TrendName = Literal["up", "down", "stable", "new"]


class MarketEntity(BaseModel):
    canonical_name: str
    canonical_slug: str
    aliases: list[str] = Field(default_factory=list)
    editorial_kind: EditorialKind
    topic_family: str
    implementation_languages: list[str] = Field(default_factory=list)
    ecosystems: list[str] = Field(default_factory=list)
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    adoption_signals: dict[str, float] = Field(default_factory=dict)
    momentum_signals: dict[str, float] = Field(default_factory=dict)
    maturity_signals: dict[str, float] = Field(default_factory=dict)
    risk_signals: dict[str, float] = Field(default_factory=dict)
    candidate_reason_inputs: list[str] = Field(default_factory=list)
    description: str | None = None


class LaneEditorialInput(BaseModel):
    lane: LaneName
    candidates: list[MarketEntity] = Field(default_factory=list)
    nearby_alternatives: dict[str, list[str]] = Field(default_factory=dict)
    exclusions: list[str] = Field(default_factory=list)
    prompt_context: list[str] = Field(default_factory=list)


class EditorialBlip(BaseModel):
    id: str
    name: str
    quadrant: str
    ring: RingName
    description: str
    trend: TrendName
    confidence: float
    updatedAt: str
    marketScore: float | None = None
    moved: int = 0
    whyThisRing: str | None = None
    whyNow: str | None = None
    useCases: list[str] = Field(default_factory=list)
    avoidWhen: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    entityType: str | None = None
    canonicalId: str | None = None
    sourceCoverage: int | None = None
    signals: dict[str, float] = Field(default_factory=dict)
    sourceFreshness: dict[str, int | None] | None = None
    evidenceSummary: dict[str, Any] | None = None
    evidence: list[str | dict[str, Any]] = Field(default_factory=list)
    owner: str | None = None
    nextStep: str | None = None
    nextReviewAt: str | None = None


class EditorialExclusion(BaseModel):
    id: str
    name: str
    reason: str
    lane: LaneName
    marketScore: float = 0.0


class LaneEditorialDecision(BaseModel):
    lane: LaneName
    included: list[EditorialBlip] = Field(default_factory=list)
    excluded: list[EditorialExclusion] = Field(default_factory=list)
    merge_notes: list[str] = Field(default_factory=list)


class EditorialDecisionBundle(BaseModel):
    decisions: list[LaneEditorialDecision] = Field(default_factory=list)

