from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from etl.canonical_mapping import deps_dev_subject_for
from etl.contracts import MarketEntity
from etl.evidence import EvidenceRecord


def enrich_market_entities_with_validation(
    entities: list[MarketEntity],
    *,
    deps_dev_source,
    osv_source,
) -> list[MarketEntity]:
    enriched = [entity.model_copy(deep=True) for entity in entities]
    entities_by_subject: dict[str, list[MarketEntity]] = defaultdict(list)
    deps_subjects: list[str] = []

    for entity in enriched:
        ecosystem = entity.ecosystems[0] if entity.ecosystems else None
        subject = deps_dev_subject_for(entity.canonical_name, ecosystem=ecosystem)
        if not subject:
            continue
        deps_subjects.append(subject)
        entities_by_subject[subject].append(entity)

    if not deps_subjects:
        return enriched

    deps_records = deps_dev_source.fetch(_unique(deps_subjects))
    version_subjects: set[str] = set()

    for record in deps_records:
        base_subject = _base_subject_id(record.subject_id)
        for entity in entities_by_subject.get(base_subject, []):
            _append_evidence(entity, record)
        if record.metric == "default_version":
            version_subjects.add(record.subject_id)

    if version_subjects:
        osv_records = osv_source.fetch(sorted(version_subjects))
        for record in osv_records:
            base_subject = _base_subject_id(record.subject_id)
            for entity in entities_by_subject.get(base_subject, []):
                _append_evidence(entity, record)

    return enriched


def _append_evidence(entity: MarketEntity, record: EvidenceRecord) -> None:
    payload = {
        "source": record.source,
        "metric": record.metric,
        "subject_id": record.subject_id,
        "raw_value": record.raw_value,
        "normalized_value": record.normalized_value,
        "observed_at": record.observed_at,
        "freshness_days": record.freshness_days,
    }
    key = (payload["source"], payload["metric"], payload["subject_id"])
    existing_keys = {
        (
            str(item.get("source", "")),
            str(item.get("metric", "")),
            str(item.get("subject_id", "")),
        )
        for item in entity.source_evidence
    }
    if key not in existing_keys:
        entity.source_evidence.append(payload)


def _base_subject_id(subject_id: str) -> str:
    return str(subject_id).split("@", 1)[0]


def _unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})
