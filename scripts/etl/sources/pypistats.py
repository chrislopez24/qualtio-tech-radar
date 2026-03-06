from datetime import datetime, timezone
from math import log10
from urllib.parse import quote
import logging

import requests

from etl.config import PyPIStatsSource as PyPIStatsConfig
from etl.evidence import EvidenceRecord

logger = logging.getLogger(__name__)


class PyPIStatsSource:
    def __init__(self, config: PyPIStatsConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Qualtio-Tech-Radar/1.0"})
        self._cache: dict[str, list[EvidenceRecord]] = {}

    def fetch(self, subjects: list[str]) -> list[EvidenceRecord]:
        if not self.config.enabled:
            return []

        evidence: list[EvidenceRecord] = []
        for subject in subjects:
            package = self._normalize_subject(subject)
            if not package:
                continue

            if package in self._cache:
                evidence.extend(self._cache[package])
                continue

            try:
                response = self.session.get(
                    f"{self.config.base_url}/packages/{quote(package, safe='')}/{self.config.period}",
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json() or {}
            except requests.RequestException as exc:
                logger.warning("PyPI stats lookup failed for %s: %s", package, exc)
                self._cache[package] = []
                continue

            data = payload.get("data") or {}
            last_month = int(data.get("last_month", 0) or 0)
            records = [self._to_evidence(package, last_month)]
            self._cache[package] = records
            evidence.extend(records)

        return evidence

    def _normalize_subject(self, subject: str) -> str | None:
        value = str(subject or "").strip().lower()
        if not value or " " in value:
            return None
        return value

    def _to_evidence(self, subject_id: str, last_month_downloads: int) -> EvidenceRecord:
        normalized_value = min(100.0, (log10(1 + max(0, last_month_downloads)) / log10(1 + 10_000_000)) * 100.0)
        return EvidenceRecord(
            source="pypistats",
            metric="downloads_last_month",
            subject_id=subject_id,
            raw_value=int(last_month_downloads),
            normalized_value=round(normalized_value, 2),
            observed_at=datetime.now(timezone.utc).isoformat(),
            freshness_days=1,
        )
