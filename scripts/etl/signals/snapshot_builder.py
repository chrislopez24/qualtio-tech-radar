from __future__ import annotations

from etl.contracts import MarketEntity
from etl.signals.scoring import score_entity


def build_market_snapshot(entities: list[MarketEntity]) -> list[MarketEntity]:
    return [score_entity(entity.model_copy(deep=True)) for entity in entities]
