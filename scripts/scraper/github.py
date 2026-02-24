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

    def _check_rate_limit(self):
        """Check GitHub API rate limit status and wait if necessary"""
        try:
            response = self.session.get('https://api.github.com/rate_limit')
            response.raise_for_status()
            data = response.json()
            
            remaining = data['resources']['core']['remaining']
            reset_timestamp = data['resources']['core']['reset']
            
            if remaining < 10:
                wait_time = max(0, reset_timestamp - int(time.time())) + 1
                print(f"Rate limit low ({remaining} remaining). Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            
        except Exception as e:
            print(f"Warning: Could not check rate limit: {e}")

    def _handle_rate_limit_error(self, retry_count: int = 0, max_retries: int = 3):
        """Handle rate limit error with exponential backoff"""
        if retry_count >= max_retries:
            raise Exception("Max retries exceeded for rate limit")
        
        wait_time = 2 ** retry_count  # Exponential backoff: 1, 2, 4, 8 seconds
        print(f"Rate limit hit. Waiting {wait_time} seconds before retry {retry_count + 1}/{max_retries}...")
        time.sleep(wait_time)
        return retry_count + 1

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
        """Use PyGithub to fetch trending repos with rate limit handling"""
        repos = []
        retry_count = 0
        max_retries = 3
        
        self._check_rate_limit()
        
        search_query = f"stars:>{min_stars} pushed:>2024-01-01"
        
        while retry_count < max_retries:
            try:
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
                    except RateLimitException:
                        retry_count = self._handle_rate_limit_error(retry_count, max_retries)
                        continue
                    except Exception as e:
                        print(f"Error processing repo {repo.full_name}: {e}")
                        continue
                
                return repos
                
            except RateLimitException:
                retry_count = self._handle_rate_limit_error(retry_count, max_retries)
            except Exception as e:
                print(f"Error fetching trending repos: {e}")
                break
                
        return repos

    def _get_trending_http(self, min_stars: int, limit: int) -> List[Repository]:
        """Fallback HTTP-based fetching with rate limit handling"""
        repos = []
        retry_count = 0
        max_retries = 3
        
        url = "https://api.github.com/search/repositories"
        params = {
            "q": f"stars:>{min_stars}",
            "sort": "stars",
            "order": "desc",
            "per_page": min(limit, 100)
        }
        
        while retry_count < max_retries:
            try:
                self._check_rate_limit()
                response = self.session.get(url, params=params)
                
                # Check for rate limiting
                if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
                    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                    if remaining == 0:
                        reset_timestamp = int(response.headers.get('X-RateLimit-Reset', 0))
                        wait_time = max(0, reset_timestamp - int(time.time())) + 1
                        print(f"Rate limit hit. Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                
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
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    retry_count = self._handle_rate_limit_error(retry_count, max_retries)
                else:
                    print(f"HTTP error: {e}")
                    break
            except Exception as e:
                print(f"Error fetching trending repos: {e}")
                break
            
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