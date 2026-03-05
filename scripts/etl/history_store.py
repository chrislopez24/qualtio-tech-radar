"""Rolling history persistence for weekly radar snapshots."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from etl.checkpoint import safe_json_write
from typing import Any, Dict, List, Optional


class HistoryStore:
    def __init__(self, file_path: Path, max_weeks: int = 12):
        self.file_path = Path(file_path)
        self.max_weeks = max(1, int(max_weeks))

    def _load_history(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []

        try:
            data = json.loads(self.file_path.read_text())
        except Exception:
            return []

        if isinstance(data, dict) and isinstance(data.get("snapshots"), list):
            return [item for item in data["snapshots"] if isinstance(item, dict)]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def _save_history(self, snapshots: List[Dict[str, Any]]) -> None:
        payload = {"snapshots": snapshots}
        safe_json_write(self.file_path, payload)

    def append_snapshot(self, snapshot: Dict[str, Any]) -> None:
        snapshots = self._load_history()
        snapshot_copy = dict(snapshot)
        snapshot_copy.setdefault("updatedAt", datetime.now().isoformat())
        snapshots.append(snapshot_copy)
        snapshots = snapshots[-self.max_weeks :]
        self._save_history(snapshots)

    def get_previous_snapshot(self) -> Optional[Dict[str, Any]]:
        snapshots = self._load_history()
        if len(snapshots) < 2:
            return None
        return snapshots[-2]

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        snapshots = self._load_history()
        if not snapshots:
            return None
        return snapshots[-1]
