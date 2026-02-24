"""GitHub Trending Source for Tech Radar"""

import os
import logging
from typing import List, Optional

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
            requests_per_minute=config.rate_limit.requests_per_minute
            if hasattr(config, "rate_limit")
            else 30,
            max_retries=config.rate_limit.max_retries
            if hasattr(config, "rate_limit")
            else 3,
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

    def _filter_by_language(self, repos: List[dict], language: Optional[str]) -> List[dict]:
        if not language:
            return repos
        return [
            repo
            for repo in repos
            if (hasattr(repo, "language") and repo.language and repo.language.lower() == language.lower())
            or (isinstance(repo, dict) and repo.get("language") and repo.get("language", "").lower() == language.lower())
        ]

    def _normalize_to_signal(self, repo) -> TechnologySignal:
        name = repo.name if hasattr(repo, "name") else repo.get("name", "")
        stars = repo.stars if hasattr(repo, "stars") else repo.get("stars", 0)
        description = (
            repo.description if hasattr(repo, "description") else repo.get("description", "")
        )
        url = repo.url if hasattr(repo, "url") else repo.get("url", "")
        language = (
            repo.language if hasattr(repo, "language") else repo.get("language")
        )
        topics = repo.topics if hasattr(repo, "topics") else repo.get("topics", [])

        max_stars = 100000
        normalized_stars = min(stars / max_stars, 1.0)
        score = normalized_stars * 10

        raw_data = {
            "name": name,
            "full_name": repo.full_name if hasattr(repo, "full_name") else repo.get("full_name", ""),
            "description": description,
            "stars": stars,
            "forks": repo.forks if hasattr(repo, "forks") else repo.get("forks", 0),
            "language": language,
            "topics": topics,
            "url": url,
            "created_at": repo.created_at if hasattr(repo, "created_at") else repo.get("created_at", ""),
            "updated_at": repo.updated_at if hasattr(repo, "updated_at") else repo.get("updated_at", ""),
        }

        return TechnologySignal(
            name=name,
            source="github_trending",
            signal_type="github_stars",
            score=score,
            raw_data=raw_data,
        )