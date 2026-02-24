"""GitHub Trending Source for Tech Radar"""

import os
import logging
from typing import List, Optional, Any

from etl.config import GitHubTrendingSource as GitHubTrendingConfig
from etl.models import TechnologySignal
from etl.rate_limiter import GitHubRateLimiter
from scraper.github import GitHubScraper

logger = logging.getLogger(__name__)


class GitHubTrendingSource:
    def __init__(
        self,
        config: GitHubTrendingConfig,
        rate_limiter: Optional[GitHubRateLimiter] = None,
    ):
        self.config = config
        self.rate_limiter = rate_limiter or GitHubRateLimiter(
            requests_per_minute=getattr(config, "rate_limit", None) and config.rate_limit.requests_per_minute or 30,
            max_retries=getattr(config, "rate_limit", None) and config.rate_limit.max_retries or 3,
        )
        self.scraper = GitHubScraper(token=self.rate_limiter.token)

    def fetch(self) -> List[TechnologySignal]:
        if not self.config.enabled:
            return []

        language = self.config.language if self.config.language != "all" else None
        time_range = self.config.time_range

        repos = self._fetch_trending_repos(language=language, time_range=time_range)

        signals = []
        for repo in repos:
            signal = self._normalize_to_signal(repo)
            signals.append(signal)

        return signals

    def _fetch_trending_repos(
        self, language: Optional[str] = None, time_range: str = "daily"
    ) -> List[dict]:
        try:
            repos = self.rate_limiter.execute_with_backoff(
                self.scraper.get_trending_repos,
                min_stars=100,
                limit=50,
            )
            return self._filter_by_language(repos, language)
        except Exception as e:
            logger.error(f"Error fetching trending repos: {e}")
            return []

    def _get_repo_attr(self, repo, attr: str, default: Any = None) -> Any:
        if isinstance(repo, dict):
            return repo.get(attr, default)
        return getattr(repo, attr, default)

    def _filter_by_language(self, repos: List[dict], language: Optional[str]) -> List[dict]:
        if not language:
            return repos
        return [
            repo
            for repo in repos
            if self._get_repo_attr(repo, "language") and self._get_repo_attr(repo, "language", "").lower() == language.lower()
        ]

    def _normalize_to_signal(self, repo) -> TechnologySignal:
        name = self._get_repo_attr(repo, "name", "")
        stars = self._get_repo_attr(repo, "stars", 0)
        description = self._get_repo_attr(repo, "description", "")
        url = self._get_repo_attr(repo, "url", "")
        language = self._get_repo_attr(repo, "language")
        topics = self._get_repo_attr(repo, "topics", [])

        max_stars = 100000
        normalized_stars = min(stars / max_stars, 1.0)
        score = normalized_stars * 10

        raw_data = {
            "name": name,
            "full_name": self._get_repo_attr(repo, "full_name", ""),
            "description": description,
            "stars": stars,
            "forks": self._get_repo_attr(repo, "forks", 0),
            "language": language,
            "topics": topics,
            "url": url,
            "created_at": self._get_repo_attr(repo, "created_at", ""),
            "updated_at": self._get_repo_attr(repo, "updated_at", ""),
        }

        return TechnologySignal(
            name=name,
            source="github_trending",
            signal_type="github_stars",
            score=score,
            raw_data=raw_data,
        )