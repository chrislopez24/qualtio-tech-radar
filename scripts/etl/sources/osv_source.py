from datetime import datetime, timezone
import logging
from pathlib import Path

import requests

from etl.config import OSVSource as OSVConfig
from etl.evidence import EvidenceRecord
from etl.source_cache import SourceCache

logger = logging.getLogger(__name__)


class OSVSource:
    def __init__(self, config: OSVConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Qualtio-Tech-Radar/1.0"})
        self._cache: dict[str, list[EvidenceRecord]] = {}
        self._persistent_cache = SourceCache(Path(config.cache_file))

    def fetch(self, subjects: list[str]) -> list[EvidenceRecord]:
        if not self.config.enabled:
            return []

        parsed_subjects = [parsed for parsed in (self._parse_subject(subject) for subject in subjects) if parsed]
        if not parsed_subjects:
            return []

        evidence: list[EvidenceRecord] = []
        missing_subjects: list[tuple[str, str, str]] = []

        for ecosystem, package, version in parsed_subjects:
            cache_key = f"{ecosystem}:{package}@{version}"
            if cache_key in self._cache:
                evidence.extend(self._cache[cache_key])
                continue

            persistent_hit = self._persistent_cache.get(cache_key)
            if persistent_hit is not None:
                records = [self._record_from_cache(item) for item in persistent_hit.value or []]
                self._cache[cache_key] = records
                evidence.extend(records)
                continue

            missing_subjects.append((ecosystem, package, version))

        if not missing_subjects:
            return evidence

        queries = [
            {
                "package": {
                    "ecosystem": self._normalize_ecosystem(ecosystem),
                    "name": package,
                },
                "version": version,
            }
            for ecosystem, package, version in missing_subjects
        ]

        try:
            response = self.session.post(
                f"{self.config.base_url}/querybatch",
                json={"queries": queries},
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json() or {}
        except requests.RequestException as exc:
            logger.warning("OSV querybatch failed for %s: %s", queries, exc)
            return evidence

        results = payload.get("results") or []
        for (ecosystem, package, version), result in zip(missing_subjects, results):
            cache_key = f"{ecosystem}:{package}@{version}"
            vuln_count = len(result.get("vulns") or [])
            record = self._to_evidence(cache_key, vuln_count)
            records = [record]
            self._cache[cache_key] = records
            self._persistent_cache.put(
                cache_key,
                [self._record_to_cache(record)],
                ttl_seconds=self.config.cache_ttl_seconds,
            )
            evidence.extend(records)

        self._persistent_cache.flush()
        return evidence

    def _parse_subject(self, subject: str) -> tuple[str, str, str] | None:
        value = str(subject or "").strip().lower()
        if ":" not in value or "@" not in value:
            return None
        ecosystem, package_version = value.split(":", 1)
        package, version = package_version.rsplit("@", 1)
        if not ecosystem or not package or not version:
            return None
        return ecosystem, package, version

    def _to_evidence(self, subject_id: str, vulnerability_count: int) -> EvidenceRecord:
        return EvidenceRecord(
            source="osv",
            metric="known_vulnerabilities",
            subject_id=subject_id,
            raw_value=int(vulnerability_count),
            normalized_value=min(100.0, float(vulnerability_count * 20)),
            observed_at=datetime.now(timezone.utc).isoformat(),
            freshness_days=1,
        )

    def _normalize_ecosystem(self, ecosystem: str) -> str:
        mapping = {
            "pypi": "PyPI",
            "npm": "npm",
            "cargo": "crates.io",
            "go": "Go",
            "rubygems": "RubyGems",
        }
        return mapping.get(ecosystem, ecosystem)

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
