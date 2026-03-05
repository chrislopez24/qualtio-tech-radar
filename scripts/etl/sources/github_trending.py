"""GitHub Trending Source for Tech Radar"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Any

from etl.config import GitHubTrendingSource as GitHubTrendingConfig
from etl.models import TechnologySignal
from etl.rate_limiter import GitHubRateLimiter
from etl.sources.github_scraper import GitHubScraper

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
            days = self._time_range_to_days(time_range)
            since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
            
            all_repos = []

            # Strategy 1: Repos with recent push activity
            pushed_query = f"pushed:>={since}"
            if language:
                pushed_query = f"{pushed_query} language:{language}"

            recent_repos = self.rate_limiter.execute_with_backoff(
                self.scraper.search_repositories,
                query=pushed_query,
                sort="stars",
                order="desc",
                limit=100,
            )
            all_repos.extend(recent_repos)
            logger.info(f"GitHub: Found {len(recent_repos)} repos with recent activity")

            # Strategy 2: Recently created repos
            created_query = f"created:>={since}"
            if language:
                created_query = f"{created_query} language:{language}"

            new_repos = self.rate_limiter.execute_with_backoff(
                self.scraper.search_repositories,
                query=created_query,
                sort="stars",
                order="desc",
                limit=50,
            )
            all_repos.extend(new_repos)
            logger.info(f"GitHub: Found {len(new_repos)} newly created repos")

            merged = self._merge_repo_results(all_repos)
            return self._filter_by_language(merged, language)
        except Exception as e:
            logger.error(f"Error fetching trending repos: {e}")
            return []

    def _time_range_to_days(self, time_range: str) -> int:
        if time_range == "monthly":
            return 30
        if time_range == "weekly":
            return 7
        return 1

    def _merge_repo_results(self, repos: List[dict]) -> List[dict]:
        by_full_name: dict[str, dict] = {}
        for repo in repos:
            full_name = self._get_repo_attr(repo, "full_name", "")
            key = full_name or self._get_repo_attr(repo, "name", "")
            if not key:
                continue

            existing = by_full_name.get(key)
            if existing is None:
                repo_copy = self._repo_to_dict(repo)
                repo_copy["gh_momentum"] = self._calculate_momentum_proxy(repo_copy)
                by_full_name[key] = repo_copy
                continue

            existing["stars"] = max(existing.get("stars", 0), self._get_repo_attr(repo, "stars", 0))
            existing["forks"] = max(existing.get("forks", 0), self._get_repo_attr(repo, "forks", 0))
            existing["updated_at"] = max(
                str(existing.get("updated_at", "")),
                str(self._get_repo_attr(repo, "updated_at", "")),
            )
            existing["created_at"] = min(
                str(existing.get("created_at", "")),
                str(self._get_repo_attr(repo, "created_at", "")),
            )
            existing["gh_momentum"] = self._calculate_momentum_proxy(existing)

        return list(by_full_name.values())

    def _repo_to_dict(self, repo: Any) -> dict:
        if isinstance(repo, dict):
            return dict(repo)

        return {
            "name": self._get_repo_attr(repo, "name", ""),
            "full_name": self._get_repo_attr(repo, "full_name", ""),
            "description": self._get_repo_attr(repo, "description", ""),
            "stars": self._get_repo_attr(repo, "stars", 0),
            "forks": self._get_repo_attr(repo, "forks", 0),
            "language": self._get_repo_attr(repo, "language"),
            "topics": self._get_repo_attr(repo, "topics", []),
            "url": self._get_repo_attr(repo, "url", ""),
            "created_at": self._get_repo_attr(repo, "created_at", ""),
            "updated_at": self._get_repo_attr(repo, "updated_at", ""),
        }

    def _calculate_momentum_proxy(self, repo: dict) -> float:
        stars = float(repo.get("stars", 0))
        forks = float(repo.get("forks", 0))
        return min(100.0, stars / 100.0 + forks / 20.0)

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
            "gh_momentum": self._get_repo_attr(repo, "gh_momentum", 0.0),
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
