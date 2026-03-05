"""Checkpoint support for long-running ETL pipeline executions.

Provides checkpoint save/load functionality to enable resuming
pipeline executions from the last checkpoint.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def safe_json_write(path: Path, data: Any, indent: int = 2) -> None:
    """Atomically write JSON data to file using temp file + rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        'w', dir=path.parent, delete=False, suffix='.tmp'
    ) as tmp:
        try:
            json.dump(data, tmp, indent=indent, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
        except Exception:
            os.unlink(tmp.name)
            raise
    os.replace(tmp.name, str(path))


class CheckpointStore:
    """Store and load pipeline checkpoints for resumable executions."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def save(self, data: Dict[str, Any]) -> None:
        """Save checkpoint data to disk."""
        safe_json_write(self.path, data)
        logger.debug(f"Checkpoint saved to {self.path}")

    def load(self) -> Optional[Dict[str, Any]]:
        """Load checkpoint data from disk."""
        if not self.path.exists():
            logger.debug(f"No checkpoint found at {self.path}")
            return None
        with open(self.path, 'r') as f:
            data = json.load(f)
        logger.debug(f"Checkpoint loaded from {self.path}")
        return data

    def clear(self) -> None:
        """Clear checkpoint file."""
        if self.path.exists():
            self.path.unlink()
            logger.debug(f"Checkpoint cleared at {self.path}")