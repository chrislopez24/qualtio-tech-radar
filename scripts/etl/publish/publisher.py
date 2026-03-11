from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PUBLIC_QUADRANT_MAP = {"frameworks": "tools"}
REQUIRED_FIELDS = {"id", "name", "quadrant", "ring", "description", "trend", "confidence", "updatedAt"}


def publish_radar(payload: dict, output_path: Path) -> dict:
    output = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "technologies": [_normalize_public_blip(blip) for blip in payload.get("blips", [])],
        "watchlist": [_normalize_public_blip(blip) for blip in payload.get("watchlist", [])],
        "meta": payload.get("meta", {}),
    }

    for item in [*output["technologies"], *output["watchlist"]]:
        missing = REQUIRED_FIELDS - item.keys()
        if missing:
            raise ValueError(f"Invalid public radar item, missing: {sorted(missing)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n")
    return output


def _normalize_public_blip(blip: dict) -> dict:
    normalized = dict(blip)
    normalized["quadrant"] = PUBLIC_QUADRANT_MAP.get(normalized.get("quadrant"), normalized.get("quadrant"))
    normalized.setdefault("moved", 0)
    normalized.setdefault("useCases", [])
    normalized.setdefault("avoidWhen", [])
    normalized.setdefault("alternatives", [])
    return {key: value for key, value in normalized.items() if value is not None}
