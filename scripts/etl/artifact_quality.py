from __future__ import annotations

from typing import Any

from etl.ai_filter import (
    is_resource_like_repository,
    is_strong_ring_editorially_eligible,
    is_trial_ring_editorially_eligible,
)


QUADRANT_NAMES = ("platforms", "techniques", "tools", "languages")
RING_NAMES = ("adopt", "trial", "assess", "hold")

EDITORIAL_FAILURE_STATUSES = {"invalid", "editorial-failed"}


def _missing_snapshot() -> dict[str, Any]:
    return {
        "count": 0,
        "avgMarketScore": 0.0,
        "githubOnlyRatio": 0.0,
        "resourceLikeCount": 0,
        "editoriallyWeakCount": 0,
        "topSuspicious": [],
        "status": "missing",
    }


def _empty_snapshot() -> dict[str, Any]:
    snapshot = _missing_snapshot()
    snapshot["status"] = "good"
    return snapshot


def is_github_only_signal(entry: dict[str, Any]) -> bool:
    evidence_summary = entry.get("evidenceSummary")
    if isinstance(evidence_summary, dict) and "githubOnly" in evidence_summary:
        return bool(evidence_summary.get("githubOnly"))

    source_coverage = entry.get("sourceCoverage")
    if source_coverage is not None:
        try:
            if int(source_coverage) > 1:
                return False
        except Exception:
            pass

    signals = entry.get("signals", {})
    if not isinstance(signals, dict):
        return False
    gh_momentum = float(signals.get("ghMomentum", 0.0) or 0.0)
    gh_popularity = float(signals.get("ghPopularity", 0.0) or 0.0)
    hn_heat = float(signals.get("hnHeat", 0.0) or 0.0)
    has_github_signal = gh_momentum > 0.0 or gh_popularity > 0.0
    return has_github_signal and hn_heat <= 0.0


def _append_unique_reasons(reasons: list[str], new_reasons: list[str]) -> None:
    for reason in new_reasons:
        if reason and reason not in reasons:
            reasons.append(reason)


def quality_snapshot(entries: list[dict[str, Any]], *, strong_ring: str | None = None) -> dict[str, Any]:
    count = len(entries)
    if count == 0:
        return _empty_snapshot()

    github_only_entries: list[dict[str, Any]] = []
    top_suspicious: list[dict[str, Any]] = []
    resource_like_count = 0
    editorially_weak_count = 0

    for entry in entries:
        reasons: list[str] = []
        description = str(entry.get("description", ""))
        entry_id = str(entry.get("id", ""))
        effective_ring = strong_ring or str(entry.get("ring", ""))
        editorial_flags = [str(flag) for flag in entry.get("editorialFlags", []) if flag]
        editorial_status = str(entry.get("editorialStatus", ""))
        is_editorially_weak = False

        if is_github_only_signal(entry):
            github_only_entries.append(entry)
            reasons.append("githubOnly")
        if is_resource_like_repository(entry_id, description):
            resource_like_count += 1
            reasons.append("resourceLike")
        elif effective_ring == "adopt" and not is_strong_ring_editorially_eligible(
            str(entry.get("name", "")),
            description,
            [],
        ):
            is_editorially_weak = True
            reasons.append("editoriallyWeak")
        elif effective_ring == "trial" and not is_trial_ring_editorially_eligible(
            str(entry.get("name", "")),
            description,
            [],
        ):
            is_editorially_weak = True
            reasons.append("editoriallyWeak")

        if editorial_flags:
            is_editorially_weak = True
            _append_unique_reasons(reasons, editorial_flags)
        elif editorial_status in EDITORIAL_FAILURE_STATUSES:
            is_editorially_weak = True

        if is_editorially_weak:
            editorially_weak_count += 1

        if reasons:
            top_suspicious.append(
                {
                    "id": entry_id,
                    "name": str(entry.get("name", "")),
                    "marketScore": round(float(entry.get("marketScore", 0.0) or 0.0), 2),
                    "reasons": reasons,
                }
            )

    avg_market_score = round(
        sum(float(entry.get("marketScore", 0.0) or 0.0) for entry in entries) / count,
        2,
    )
    github_only_ratio = round(len(github_only_entries) / count, 4)
    top_suspicious.sort(key=lambda entry: float(entry.get("marketScore", 0.0)), reverse=True)

    status = "good"
    if strong_ring in {"adopt", "trial"}:
        strong_ring_low_score = (
            strong_ring == "adopt" and avg_market_score < 80.0
        ) or (
            strong_ring == "trial" and avg_market_score < 60.0
        )
        if (
            github_only_ratio >= 0.5
            or resource_like_count > 0
            or editorially_weak_count > 0
            or strong_ring_low_score
        ):
            status = "bad"
    elif github_only_ratio >= 0.5 or resource_like_count > 0 or editorially_weak_count > 0:
        status = "warn"

    return {
        "count": count,
        "avgMarketScore": avg_market_score,
        "githubOnlyRatio": github_only_ratio,
        "resourceLikeCount": resource_like_count,
        "editoriallyWeakCount": editorially_weak_count,
        "topSuspicious": top_suspicious[:5],
        "status": status,
    }


def build_artifact_quality(technologies: list[dict[str, Any]]) -> dict[str, Any]:
    ring_quality = {
        ring: quality_snapshot(
            [entry for entry in technologies if str(entry.get("ring", "")) == ring],
            strong_ring=ring,
        )
        for ring in RING_NAMES
    }

    quadrant_quality = {
        quadrant: (
            quality_snapshot([entry for entry in technologies if str(entry.get("quadrant", "")) == quadrant])
            if any(str(entry.get("quadrant", "")) == quadrant for entry in technologies)
            else _missing_snapshot()
        )
        for quadrant in QUADRANT_NAMES
    }

    quadrant_ring_quality = {
        quadrant: {
            ring: (
                quality_snapshot(
                    [
                        entry
                        for entry in technologies
                        if str(entry.get("quadrant", "")) == quadrant and str(entry.get("ring", "")) == ring
                    ],
                    strong_ring=ring,
                )
                if any(
                    str(entry.get("quadrant", "")) == quadrant and str(entry.get("ring", "")) == ring
                    for entry in technologies
                )
                else _missing_snapshot()
            )
            for ring in RING_NAMES
        }
        for quadrant in QUADRANT_NAMES
    }

    return {
        "ringQuality": ring_quality,
        "quadrantQuality": quadrant_quality,
        "quadrantRingQuality": quadrant_ring_quality,
    }
