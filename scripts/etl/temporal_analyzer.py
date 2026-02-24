"""Temporal analyzer module for computing trend labels and activity scores"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional

from etl.models import TechnologySignal, TemporalAnalysis


RECENT_DAYS = 50
NEW_DAYS = 7
LEGACY_DAYS = 120


class TemporalAnalyzer:
    def __init__(self, recent_days: int = RECENT_DAYS, new_days: int = NEW_DAYS, legacy_days: int = LEGACY_DAYS):
        self.recent_days = recent_days
        self.new_days = new_days
        self.legacy_days = legacy_days

    def analyze(
        self,
        signals: List[TechnologySignal],
        include_domain_breakdown: bool = False
    ) -> TemporalAnalysis:
        """Analyze temporal distribution of signals and compute trend/activity"""

        if not signals:
            return TemporalAnalysis(
                trend="stable",
                activity_score=0.0,
                recent_count=0,
                new_count=0,
                legacy_count=0
            )

        now = datetime.now()
        buckets = {"recent": 0, "new": 0, "legacy": 0}
        domain_scores: Dict[str, List[float]] = {}

        for signal in signals:
            date = self._extract_date(signal)
            if date:
                days_ago = (now - date).days

                if days_ago <= self.new_days:
                    buckets["new"] += 1
                elif days_ago <= self.recent_days:
                    buckets["recent"] += 1
                else:
                    buckets["legacy"] += 1

            if include_domain_breakdown:
                source = signal.source
                if source not in domain_scores:
                    domain_scores[source] = []
                domain_scores[source].append(signal.score)

        total = len(signals)
        recent_pct = buckets["recent"] / total
        new_pct = buckets["new"] / total
        legacy_pct = buckets["legacy"] / total

        trend = self._compute_trend(buckets, total)
        activity_score = self._compute_activity_score(signals, buckets)

        domain_breakdown = None
        if include_domain_breakdown and domain_scores:
            domain_breakdown = {
                source: sum(scores) / len(scores)
                for source, scores in domain_scores.items()
            }

        return TemporalAnalysis(
            trend=trend,
            activity_score=activity_score,
            recent_count=buckets["recent"],
            new_count=buckets["new"],
            legacy_count=buckets["legacy"],
            domain_breakdown=domain_breakdown
        )

    def _extract_date(self, signal: TechnologySignal) -> Optional[datetime]:
        """Extract date from signal raw_data"""
        date_str = signal.raw_data.get("trending_date")
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def _compute_trend(self, buckets: Dict[str, int], total: int) -> str:
        """Compute trend label based on bucket distribution"""
        recent_pct = buckets["recent"] / total
        new_pct = buckets["new"] / total
        legacy_pct = buckets["legacy"] / total

        if new_pct >= 0.8:
            return "new"
        elif recent_pct > 0.5:
            return "growing"
        elif legacy_pct >= 0.6:
            return "declining"
        else:
            return "stable"

    def _compute_activity_score(self, signals: List[TechnologySignal], buckets: Dict[str, int]) -> float:
        """Compute activity score based on signal scores and recency"""
        now = datetime.now()
        total_score = 0.0

        for signal in signals:
            date = self._extract_date(signal)
            recency_weight = 1.0

            if date:
                days_ago = (now - date).days
                if days_ago <= self.new_days:
                    recency_weight = 1.5
                elif days_ago <= self.recent_days:
                    recency_weight = 1.2
                elif days_ago > self.legacy_days:
                    recency_weight = 0.5

            total_score += signal.score * recency_weight

        avg_score = total_score / len(signals)
        return min(avg_score, 10.0)