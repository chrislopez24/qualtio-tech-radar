from __future__ import annotations

from etl.canonical.entities import merge_entities
from etl.canonical.seeds import build_seed_lookup
from etl.contracts import MarketEntity


SEED_LOOKUP = build_seed_lookup()
ECOSYSTEM_LANGUAGE_MAP = {
    "npm": ["javascript", "typescript"],
    "pypi": ["python"],
    "cargo": ["rust"],
    "maven": ["java", "kotlin"],
    "go": ["go"],
}


def _normalize_name(name: str) -> str:
    return str(name or "").strip().lower()


def resolve_market_entity(name: str, hints: dict | None = None) -> MarketEntity:
    hints = hints or {}
    normalized = _normalize_name(name)
    seed = SEED_LOOKUP.get(normalized)
    ecosystem = str(hints.get("ecosystem", "")).strip().lower()
    description = hints.get("description")

    if seed is not None:
        implementation_languages = list(seed.get("implementation_languages", []))
        if ecosystem and not implementation_languages:
            implementation_languages = ECOSYSTEM_LANGUAGE_MAP.get(ecosystem, [])

        source_evidence = list(hints.get("source_evidence", []))
        if not source_evidence:
            source_evidence = [
                {
                    "source": "seed_catalog",
                    "metric": "curated_presence",
                    "normalized_value": 72.0,
                }
            ]

        return MarketEntity(
            canonical_name=seed["canonical_name"],
            canonical_slug=seed["canonical_slug"],
            aliases=list(seed.get("aliases", [])),
            editorial_kind=seed["editorial_kind"],
            topic_family=seed["topic_family"],
            implementation_languages=implementation_languages,
            ecosystems=sorted(set([*seed.get("ecosystems", []), *([ecosystem] if ecosystem else [])])),
            source_evidence=source_evidence,
            candidate_reason_inputs=list(hints.get("candidate_reason_inputs", [])),
            description=description or seed.get("description"),
        )

    editorial_kind = _infer_editorial_kind(normalized, ecosystem)
    return MarketEntity(
        canonical_name=str(name).strip() or "Unknown",
        canonical_slug=normalized.replace(" ", "-"),
        editorial_kind=editorial_kind,
        topic_family=str(hints.get("topic_family") or "general"),
        implementation_languages=ECOSYSTEM_LANGUAGE_MAP.get(ecosystem, []),
        ecosystems=[ecosystem] if ecosystem else [],
        aliases=[],
        source_evidence=list(hints.get("source_evidence", [])),
        candidate_reason_inputs=list(hints.get("candidate_reason_inputs", [])),
        description=description if isinstance(description, str) else None,
    )


def resolve_market_entities(records: list[dict]) -> list[MarketEntity]:
    entities: dict[str, MarketEntity] = {}
    for record in records:
        entity = resolve_market_entity(str(record.get("name", "")), record)
        current = entities.get(entity.canonical_slug)
        entities[entity.canonical_slug] = merge_entities(current, entity) if current else entity
    return list(entities.values())


def _infer_editorial_kind(normalized_name: str, ecosystem: str) -> str:
    if ecosystem in {"npm", "pypi", "maven", "cargo"}:
        return "tool"
    if normalized_name.endswith("db") or normalized_name in {"aws", "azure", "gcp"}:
        return "platform"
    return "tool"
