from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunMetrics:
    sources: dict[str, dict[str, Any]] = field(default_factory=dict)

    def record_source(
        self,
        name: str,
        records: int,
        duration_seconds: float,
        *,
        failures: int = 0,
    ) -> None:
        entry = self.sources.setdefault(
            name,
            {
                "records": 0,
                "durationSeconds": 0.0,
                "failures": 0,
            },
        )
        entry["records"] += max(0, int(records))
        entry["durationSeconds"] = round(float(entry["durationSeconds"]) + max(0.0, float(duration_seconds)), 4)
        entry["failures"] += max(0, int(failures))

    def to_dict(self) -> dict[str, Any]:
        return {"sources": self.sources}
