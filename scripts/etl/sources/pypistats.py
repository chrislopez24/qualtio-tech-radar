from datetime import datetime, timezone
from math import log10
from pathlib import Path
from urllib.parse import quote
import logging

import requests

from etl.config import PyPIStatsSource as PyPIStatsConfig
from etl.evidence import EvidenceRecord
from etl.source_cache import SourceCache

logger = logging.getLogger(__name__)


class PyPIStatsSource:
    def __init__(self, config: PyPIStatsConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Qualtio-Tech-Radar/1.0"})
        self._cache: dict[str, list[EvidenceRecord]] = {}
        self._persistent_cache = SourceCache(Path(config.cache_file))

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

            persistent_hit = self._persistent_cache.get(package)
            if persistent_hit is not None:
                if persistent_hit.negative:
                    self._cache[package] = []
                    continue
                records = [self._record_from_cache(item) for item in persistent_hit.value or []]
                self._cache[package] = records
                evidence.extend(records)
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
                if self._should_negative_cache_exception(exc):
                    self._persistent_cache.put_negative(
                        package,
                        ttl_seconds=self.config.negative_cache_ttl_seconds,
                    )
                continue

            data = payload.get("data") or {}
            last_month = int(data.get("last_month", 0) or 0)
            records = [self._to_evidence(package, last_month)]
            self._cache[package] = records
            self._persistent_cache.put(
                package,
                [self._record_to_cache(record) for record in records],
                ttl_seconds=self.config.cache_ttl_seconds,
            )
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

    def _record_to_cache(self, record: EvidenceRecord) -> dict:
        return {
            "source": record.source,
            "metric": record.metric,
            "subject_id": record.subject_id,
            "raw_value": record.raw_value,
            "normalized_value": record.normalized_value,
            "observed_at": record.observed_at,
            "freshness_days": record.freshness_days,
        }

    def _record_from_cache(self, payload: dict) -> EvidenceRecord:
        return EvidenceRecord(
            source=str(payload["source"]),
            metric=str(payload["metric"]),
            subject_id=str(payload["subject_id"]),
            raw_value=payload["raw_value"],
            normalized_value=float(payload["normalized_value"]),
            observed_at=str(payload["observed_at"]),
            freshness_days=int(payload["freshness_days"]),
        )

    def _should_negative_cache_exception(self, exc: requests.RequestException) -> bool:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        return status_code == 404
