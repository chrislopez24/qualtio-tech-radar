"""GitHub Trending Scraper for Tech Radar"""

import os
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests
from github import Github
from github.GithubException import RateLimitException


@dataclass
class Repository:
    name: str
    full_name: str
    description: str
    stars: int
    forks: int
    language: Optional[str]
    topics: List[str]
    url: str
    created_at: str
    updated_at: str


class GitHubScraper:
    """Scraper for GitHub trending repositories"""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        self.client = Github(self.token) if self.token else None
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Qualtio-Tech-Radar'
        })
        if self.token:
            self.session.headers.update({'Authorization': f'token {self.token}'})

    def get_trending_repos(self, min_stars: int = 100, limit: int = 50) -> List[Repository]:
        """Fetch trending repositories"""
        repos = []
        
        try:
            if self.client:
                repos = self._get_trending_github_api(min_stars, limit)
            else:
                repos = self._get_trending_http(min_stars, limit)
        except Exception as e:
            print(f"Error fetching trending repos: {e}")
            
        return repos

    def _get_trending_github_api(self, min_stars: int, limit: int) -> List[Repository]:
        """Use PyGithub to fetch trending repos"""
        repos = []
        
        search_query = f"stars:>{min_stars} pushed:>2024-01-01"
        results = self.client.search_repositories(search_query, sort="stars", order="desc")
        
        for repo in results[:limit]:
            try:
                repos.append(Repository(
                    name=repo.name,
                    full_name=repo.full_name,
                    description=repo.description or "",
                    stars=repo.stargazers_count,
                    forks=repo.forks_count,
                    language=repo.language,
                    topics=repo.get_topics() if hasattr(repo, 'get_topics') else [],
                    url=repo.html_url,
                    created_at=repo.created_at.isoformat(),
                    updated_at=repo.updated_at.isoformat()
                ))
            except Exception as e:
                print(f"Error processing repo {repo.full_name}: {e}")
                continue
                
        return repos

    def _get_trending_http(self, min_stars: int, limit: int) -> List[Repository]:
        """Fallback HTTP-based fetching"""
        repos = []
        
        url = "https://api.github.com/search/repositories"
        params = {
            "q": f"stars:>{min_stars}",
            "sort": "stars",
            "order": "desc",
            "per_page": min(limit, 100)
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        for item in data.get('items', []):
            repos.append(Repository(
                name=item['name'],
                full_name=item['full_name'],
                description=item.get('description', ''),
                stars=item['stargazers_count'],
                forks=item['forks_count'],
                language=item.get('language'),
                topics=item.get('topics', []),
                url=item['html_url'],
                created_at=item['created_at'],
                updated_at=item['updated_at']
            ))
            
        return repos

    def get_repo_details(self, full_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a repository"""
        if self.client:
            try:
                repo = self.client.get_repo(full_name)
                return {
                    'name': repo.name,
                    'full_name': repo.full_name,
                    'description': repo.description,
                    'stars': repo.stargazers_count,
                    'forks': repo.forks_count,
                    'language': repo.language,
                    'topics': repo.get_topics() if hasattr(repo, 'get_topics') else [],
                    'url': repo.html_url,
                    'license': repo.license.name if repo.license else None,
                    'contributors': min(repo.get_contributors(per_page=10).totalCount, 10),
                    'readme': self._get_readme_content(repo)
                }
            except Exception as e:
                print(f"Error fetching repo details: {e}")
                
        return None

    def _get_readme_content(self, repo) -> Optional[str]:
        """Get repository README content"""
        try:
            contents = repo.get_contents('README.md')
            if contents:
                import base64
                return base64.b64decode(contents.content).decode('utf-8')
        except:
            pass
        return None


def main():
    """Test the scraper"""
    scraper = GitHubScraper()
    repos = scraper.get_trending_repos(min_stars=100, limit=10)
    
    print(f"Found {len(repos)} trending repositories:")
    for repo in repos:
        print(f"  - {repo.full_name}: {repo.stars} stars ({repo.language})")


if __name__ == "__main__":
    main()