import logging
from datetime import datetime, timezone
from math import log10
from pathlib import Path
from urllib.parse import quote

import requests

from etl.config import DepsDevSource as DepsDevConfig
from etl.evidence import EvidenceRecord
from etl.source_cache import SourceCache

logger = logging.getLogger(__name__)


class DepsDevSource:
    def __init__(self, config: DepsDevConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Qualtio-Tech-Radar/1.0"})
        self._cache: dict[str, list[EvidenceRecord]] = {}
        self._persistent_cache = SourceCache(Path(config.cache_file))

    def fetch(self, subjects: list[str]) -> list[EvidenceRecord]:
        if not self.config.enabled:
            return []

        evidence: list[EvidenceRecord] = []
        try:
            for subject in subjects:
                if subject in self._cache:
                    evidence.extend(self._cache[subject])
                    continue

                persistent_hit = self._persistent_cache.get(subject)
                if persistent_hit is not None:
                    if persistent_hit.negative:
                        self._cache[subject] = []
                        continue
                    records = [self._record_from_cache(item) for item in persistent_hit.value or []]
                    self._cache[subject] = records
                    evidence.extend(records)
                    continue

                parsed = self._parse_subject(subject)
                if parsed is None:
                    continue

                system, package = parsed
                try:
                    version = self._fetch_default_version(system, package)
                    if not version:
                        self._cache[subject] = []
                        self._persistent_cache.put_negative(
                            subject,
                            ttl_seconds=self.config.negative_cache_ttl_seconds,
                        )
                        continue

                    dependent_count = self._fetch_dependents_count(system, package, version)
                    if dependent_count is None:
                        self._cache[subject] = []
                        self._persistent_cache.put_negative(
                            subject,
                            ttl_seconds=self.config.negative_cache_ttl_seconds,
                        )
                        continue
                except requests.RequestException as exc:
                    logger.warning("deps.dev lookup failed for %s: %s", subject, exc)
                    self._cache[subject] = []
                    if self._should_negative_cache_exception(exc):
                        self._persistent_cache.put_negative(
                            subject,
                            ttl_seconds=self.config.negative_cache_ttl_seconds,
                        )
                    continue

                records = [
                    self._to_evidence(f"{system}:{package}", dependent_count),
                    self._to_version_evidence(f"{system}:{package}@{version}", version),
                ]
                self._cache[subject] = records
                self._persistent_cache.put(
                    subject,
                    [self._record_to_cache(record) for record in records],
                    ttl_seconds=self.config.cache_ttl_seconds,
                )
                evidence.extend(records)
        finally:
            self._persistent_cache.flush()

        return evidence

    def _parse_subject(self, subject: str) -> tuple[str, str] | None:
        value = str(subject or "").strip().lower()
        if ":" not in value or " " in value:
            return None
        system, package = value.split(":", 1)
        if not system or not package:
            return None
        return system, package

    def _fetch_default_version(self, system: str, package: str) -> str | None:
        encoded_package = quote(package, safe="")
        response = self.session.get(
            f"{self.config.base_url}/v3alpha/systems/{system}/packages/{encoded_package}",
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json() or {}
        version_key = payload.get("defaultVersionKey") or {}
        default_version = str(version_key.get("version") or "").strip()
        if default_version:
            return default_version

        for version in payload.get("versions", []) or []:
            if version.get("isDefault"):
                resolved = str((version.get("versionKey") or {}).get("version") or "").strip()
                if resolved:
                    return resolved

        return None

    def _fetch_dependents_count(self, system: str, package: str, version: str) -> int | None:
        encoded_package = quote(package, safe="")
        encoded_version = quote(version, safe="")
        response = self.session.get(
            f"{self.config.base_url}/v3alpha/systems/{system}/packages/{encoded_package}/versions/{encoded_version}:dependents",
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json() or {}
        count = payload.get("totalCount")
        if count is None:
            count = payload.get("dependentCount")
        if count is None:
            count = len(payload.get("nodes", []) or payload.get("dependents", []))
        try:
            return int(count)
        except (TypeError, ValueError):
            return None

    def _to_evidence(self, subject_id: str, dependent_count: int) -> EvidenceRecord:
        normalized_value = min(100.0, (log10(1 + max(0, dependent_count)) / log10(1 + 1_000_000)) * 100.0)
        return EvidenceRecord(
            source="deps_dev",
            metric="reverse_dependents",
            subject_id=subject_id,
            raw_value=int(dependent_count),
            normalized_value=round(normalized_value, 2),
            observed_at=datetime.now(timezone.utc).isoformat(),
            freshness_days=1,
        )

    def _to_version_evidence(self, subject_id: str, version: str) -> EvidenceRecord:
        return EvidenceRecord(
            source="deps_dev",
            metric="default_version",
            subject_id=subject_id,
            raw_value=version,
            normalized_value=100.0,
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
