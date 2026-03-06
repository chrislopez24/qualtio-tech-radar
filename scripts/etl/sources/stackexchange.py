import logging
import os
from datetime import datetime, timezone
from math import log10
from urllib.parse import quote

import requests

from etl.config import StackExchangeSource as StackExchangeConfig
from etl.evidence import EvidenceRecord

logger = logging.getLogger(__name__)


class StackExchangeSource:
    def __init__(self, config: StackExchangeConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Qualtio-Tech-Radar/1.0"})
        self._cache: dict[str, list[EvidenceRecord]] = {}

    def fetch(self, subjects: list[str]) -> list[EvidenceRecord]:
        if not self.config.enabled:
            return []

        evidence: list[EvidenceRecord] = []
        for subject in subjects:
            tag = self._normalize_tag(subject)
            if not tag:
                continue

            if tag in self._cache:
                evidence.extend(self._cache[tag])
                continue

            try:
                response = self.session.get(
                    f"{self.config.base_url}/tags/{quote(tag, safe='')}/info",
                    params=self._build_params(),
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json() or {}
            except requests.RequestException as exc:
                logger.warning("Stack Exchange lookup failed for %s: %s", tag, exc)
                self._cache[tag] = []
                continue

            items = payload.get("items") or []
            if not items:
                self._cache[tag] = []
                continue

            records = [self._to_evidence(tag, items[0])]
            self._cache[tag] = records
            evidence.extend(records)

        return evidence

    def _normalize_tag(self, subject: str) -> str:
        return str(subject or "").strip().lower()

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
