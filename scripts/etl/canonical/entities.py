from __future__ import annotations

from etl.contracts import MarketEntity


def merge_entities(base: MarketEntity, incoming: MarketEntity) -> MarketEntity:
    merged = base.model_copy(deep=True)

    merged.aliases = sorted(set([*merged.aliases, *incoming.aliases]))
    merged.implementation_languages = sorted(set([*merged.implementation_languages, *incoming.implementation_languages]))
    merged.ecosystems = sorted(set([*merged.ecosystems, *incoming.ecosystems]))
    merged.source_evidence = [*merged.source_evidence, *incoming.source_evidence]
    merged.candidate_reason_inputs = sorted(set([*merged.candidate_reason_inputs, *incoming.candidate_reason_inputs]))

    if incoming.description and not merged.description:
        merged.description = incoming.description

    return merged
