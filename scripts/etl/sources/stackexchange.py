import logging
import os
import time
from datetime import datetime, timezone
from math import log10
from pathlib import Path
from urllib.parse import quote

import requests

from etl.canonical_mapping import stackexchange_tags_for
from etl.config import StackExchangeSource as StackExchangeConfig
from etl.evidence import EvidenceRecord
from etl.source_cache import SourceCache

logger = logging.getLogger(__name__)


class StackExchangeSource:
    def __init__(self, config: StackExchangeConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Qualtio-Tech-Radar/1.0"})
        self._cache: dict[str, list[EvidenceRecord]] = {}
        self._persistent_cache = SourceCache(Path(config.cache_file))
        self._backoff_until = 0.0

    def fetch(self, subjects: list[str]) -> list[EvidenceRecord]:
        if not self.config.enabled:
            return []

        evidence: list[EvidenceRecord] = []
        requests_made = 0
        for subject in subjects:
            if time.monotonic() < self._backoff_until:
                break
            if requests_made >= self.config.request_budget:
                break

            tag = self._normalize_tag(subject)
            if not tag:
                continue

            if tag in self._cache:
                evidence.extend(self._cache[tag])
                continue

            persistent_hit = self._persistent_cache.get(tag)
            if persistent_hit is not None:
                if persistent_hit.negative:
                    self._cache[tag] = []
                    continue
                records = [self._record_from_cache(item) for item in persistent_hit.value or []]
                self._cache[tag] = records
                evidence.extend(records)
                continue

            subject_records: list[EvidenceRecord] = []
            should_negative_cache = True
            for candidate_tag in self._candidate_tags(tag):
                if requests_made >= self.config.request_budget:
                    break

                try:
                    response = self.session.get(
                        f"{self.config.base_url}/tags/{quote(candidate_tag, safe='')}/info",
                        params=self._build_params(),
                        timeout=self.config.timeout_seconds,
                    )
                    requests_made += 1
                    response.raise_for_status()
                    payload = response.json() or {}
                except requests.RequestException as exc:
                    logger.warning("Stack Exchange lookup failed for %s: %s", candidate_tag, exc)
                    if self._should_negative_cache_exception(exc):
                        self._persistent_cache.put_negative(
                            tag,
                            ttl_seconds=self.config.negative_cache_ttl_seconds,
                        )
                    else:
                        should_negative_cache = False
                    if time.monotonic() < self._backoff_until:
                        break
                    continue

                backoff_seconds = int(payload.get("backoff", 0) or 0)
                if backoff_seconds > 0:
                    self._backoff_until = time.monotonic() + backoff_seconds

                items = payload.get("items") or []
                if items:
                    subject_records = [self._to_evidence(tag, items[0])]
                    break
                if backoff_seconds > 0:
                    break

            if not subject_records:
                self._cache[tag] = []
                if should_negative_cache:
                    self._persistent_cache.put_negative(
                        tag,
                        ttl_seconds=self.config.negative_cache_ttl_seconds,
                    )
                continue

            self._cache[tag] = subject_records
            self._persistent_cache.put(
                tag,
                [self._record_to_cache(record) for record in subject_records],
                ttl_seconds=self.config.cache_ttl_seconds,
            )
            evidence.extend(subject_records)

        return evidence

    def _normalize_tag(self, subject: str) -> str:
        return str(subject or "").strip().lower()

    def _candidate_tags(self, tag: str) -> list[str]:
        return stackexchange_tags_for(tag)

    def _should_negative_cache_exception(self, exc: requests.RequestException) -> bool:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        if status_code == 404:
            return True
        if status_code != 400:
            return False
        error_name = str(getattr(response, "headers", {}).get("x-error-name", "")).strip().lower()
        return error_name not in {"throttle_violation"}

    def _build_params(self) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "site": self.config.site,
            "pagesize": self.config.pagesize,
        }
        api_key = os.environ.get("STACKEXCHANGE_KEY")
        if api_key:
            params["key"] = api_key
        return params

    def _to_evidence(self, subject_id: str, payload: dict) -> EvidenceRecord:
        count = int(payload.get("count", 0) or 0)
        normalized_value = min(100.0, (log10(1 + max(0, count)) / log10(1 + 1_000_000)) * 100.0)
        return EvidenceRecord(
            source="stackexchange",
            metric="tag_activity",
            subject_id=subject_id,
            raw_value=count,
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
