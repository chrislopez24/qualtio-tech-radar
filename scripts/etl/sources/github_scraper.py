"""GitHub scraper utilities for ETL sources."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


class GitHubScraper:
    """Fetch trending-like repositories from GitHub Search API."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Qualtio-Tech-Radar",
            }
        )
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})

    def search_repositories(
        self,
        query: str = "",
        sort: str = "stars",
        order: str = "desc",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        url = "https://api.github.com/search/repositories"
        params = {
            "q": query or "stars:>100",
            "sort": sort,
            "order": order,
            "per_page": min(limit, 100),
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        return [
            {
                "name": item.get("name", ""),
                "full_name": item.get("full_name", ""),
                "description": item.get("description", ""),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "language": item.get("language"),
                "topics": item.get("topics", []),
                "url": item.get("html_url", ""),
                "created_at": item.get("created_at", ""),
                "updated_at": item.get("updated_at", ""),
            }
            for item in data.get("items", [])
        ]

    def get_trending_repos(self, min_stars: int = 100, limit: int = 50) -> List[Dict[str, Any]]:
        return self.search_repositories(
            query=f"stars:>{min_stars}",
            sort="stars",
            order="desc",
            limit=limit,
        )
