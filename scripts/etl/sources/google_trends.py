"""Google Trends Source for Tech Radar"""

import logging
from typing import List, Optional

from pytrends.request import TrendReq
from etl.config import GoogleTrendsSource as GoogleTrendsConfig
from etl.models import TechnologySignal

logger = logging.getLogger(__name__)


def build_payload(pytrends, topic: str, timeframe: str = "now 7-d"):
    pytrends.build_payload([topic], timeframe=timeframe)


class GoogleTrendsSource:
    def __init__(self, config: GoogleTrendsConfig):
        self.config = config
        self.pytrends = TrendReq(hl="en-US", tz=360)

    def fetch(self) -> List[TechnologySignal]:
        if not self.config.enabled:
            return []

        seed_topics = self.config.seed_topics
        if not seed_topics:
            logger.warning("No seed topics configured for Google Trends")
            return []

        signals = []
        seen_names = set()

        for topic in seed_topics:
            try:
                related = self._fetch_related_queries(topic)
                for item in related:
                    name = self._normalize_name(item.get("query", ""))
                    if name and name not in seen_names:
                        seen_names.add(name)
                        signal = self._normalize_to_signal(item, topic)
                        signals.append(signal)
            except Exception as e:
                logger.error(f"Error fetching Google Trends for topic {topic}: {e}")
                continue

        return signals

    def _fetch_related_queries(self, topic: str) -> List[dict]:
        self.pytrends.build_payload([topic], timeframe="now 7-d")
        related = self.pytrends.related_queries()
        return related.get(topic, [])

    def _normalize_name(self, name: str) -> str:
        name = name.strip().lower()
        name = " ".join(name.split())
        return name

    def _normalize_to_signal(self, item: dict, source_topic: str) -> TechnologySignal:
        query = item.get("query", "")
        value = item.get("value", 0)

        normalized_value = min(value / 100.0, 1.0)
        score = normalized_value * 10

        raw_data = {
            "query": query,
            "value": value,
            "source_topic": source_topic,
        }

        return TechnologySignal(
            name=query,
            source="google_trends",
            signal_type="trending_search",
            score=score,
            raw_data=raw_data,
        )