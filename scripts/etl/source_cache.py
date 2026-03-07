from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceCacheEntry:
    value: Any
    negative: bool
    observed_at: datetime
    expires_at: datetime

    def is_expired(self, *, now: datetime | None = None) -> bool:
        reference = now or datetime.now(timezone.utc)
        return reference >= self.expires_at


class SourceCache:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._data: dict[str, SourceCacheEntry] = {}
        self._load()

    def get(self, key: str, *, now: datetime | None = None) -> SourceCacheEntry | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry.is_expired(now=now):
            self._data.pop(key, None)
            self._flush()
            return None
        return entry

    def put(self, key: str, value: Any, *, ttl_seconds: int, observed_at: datetime | None = None) -> None:
        reference = observed_at or datetime.now(timezone.utc)
        self._data[key] = SourceCacheEntry(
            value=value,
            negative=False,
            observed_at=reference,
            expires_at=reference + timedelta(seconds=ttl_seconds),
        )
        self._flush()

    def put_negative(self, key: str, *, ttl_seconds: int, observed_at: datetime | None = None) -> None:
        reference = observed_at or datetime.now(timezone.utc)
        self._data[key] = SourceCacheEntry(
            value=None,
            negative=True,
            observed_at=reference,
            expires_at=reference + timedelta(seconds=ttl_seconds),
        )
        self._flush()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        parsed: dict[str, SourceCacheEntry] = {}
        for key, value in raw.items():
            parsed[key] = SourceCacheEntry(
                value=value.get("value"),
                negative=bool(value.get("negative", False)),
                observed_at=datetime.fromisoformat(value["observed_at"]),
                expires_at=datetime.fromisoformat(value["expires_at"]),
            )
        self._data = parsed

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            key: {
                "value": entry.value,
                "negative": entry.negative,
                "observed_at": entry.observed_at.isoformat(),
                "expires_at": entry.expires_at.isoformat(),
            }
            for key, entry in self._data.items()
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
