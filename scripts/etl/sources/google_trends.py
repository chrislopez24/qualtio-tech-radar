"""Google Trends Source for Tech Radar"""

import logging
from typing import List, Optional

from pytrends.request import TrendReq
from etl.config import GoogleTrendsSource as GoogleTrendsConfig
from etl.models import TechnologySignal

logger = logging.getLogger(__name__)


class GoogleTrendsSource:
    DEFAULT_TIMEFRAME = "now 7-d"

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
                        signal = self._normalize_to_signal(item, name, topic)
                        signals.append(signal)
            except Exception as e:
                logger.error(f"Error fetching Google Trends for topic {topic}: {e}")
                continue

        return signals

    def _fetch_related_queries(self, topic: str) -> List[dict]:
        try:
            self.pytrends.build_payload([topic], timeframe=self.DEFAULT_TIMEFRAME)
            related = self.pytrends.related_queries()
            
            # Handle case where response is not a dict
            if not isinstance(related, dict):
                logger.warning(f"Unexpected response type for topic '{topic}': {type(related)}")
                return []
            
            topic_data = related.get(topic)
            if not isinstance(topic_data, dict):
                logger.debug(f"No data for topic '{topic}'")
                return []
            
            rising = topic_data.get("rising")
            if not isinstance(rising, list):
                logger.debug(f"No rising queries for topic '{topic}'")
                return []
            
            return rising
        except Exception as e:
            logger.warning(f"Failed to fetch related queries for '{topic}': {e}")
            return []

    def _normalize_name(self, name: str) -> str:
        name = name.strip().lower()
        name = " ".join(name.split())
        return name

    def _normalize_to_signal(self, item: dict, name: str, source_topic: str) -> TechnologySignal:
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
            name=name,
            source="google_trends",
            signal_type="trending_search",
            score=score,
            raw_data=raw_data,
        )