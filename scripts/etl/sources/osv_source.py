from datetime import datetime, timezone
import logging

import requests

from etl.config import OSVSource as OSVConfig
from etl.evidence import EvidenceRecord

logger = logging.getLogger(__name__)


class OSVSource:
    def __init__(self, config: OSVConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Qualtio-Tech-Radar/1.0"})
        self._cache: dict[tuple[str, ...], list[EvidenceRecord]] = {}

    def fetch(self, subjects: list[str]) -> list[EvidenceRecord]:
        if not self.config.enabled:
            return []

        parsed_subjects = [parsed for parsed in (self._parse_subject(subject) for subject in subjects) if parsed]
        if not parsed_subjects:
            return []

        cache_key = tuple(f"{ecosystem}:{package}@{version}" for ecosystem, package, version in parsed_subjects)
        if cache_key in self._cache:
            return list(self._cache[cache_key])

        queries = [
            {
                "package": {
                    "ecosystem": self._normalize_ecosystem(ecosystem),
                    "name": package,
                },
                "version": version,
            }
            for ecosystem, package, version in parsed_subjects
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
            logger.warning("OSV querybatch failed for %s: %s", cache_key, exc)
            self._cache[cache_key] = []
            return []

        results = payload.get("results") or []

        evidence: list[EvidenceRecord] = []
        for (ecosystem, package, version), result in zip(parsed_subjects, results):
            vuln_count = len(result.get("vulns") or [])
            evidence.append(self._to_evidence(f"{ecosystem}:{package}@{version}", vuln_count))

        self._cache[cache_key] = list(evidence)
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
