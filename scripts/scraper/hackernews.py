"""Hacker News Scraper for Tech Radar"""

import os
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


TECH_KEYWORDS = [
    'react', 'vue', 'angular', 'svelte', 'nextjs', 'nuxt', 'remix',
    'typescript', 'javascript', 'python', 'rust', 'go', 'java', 'kotlin', 'swift',
    'docker', 'kubernetes', 'terraform', 'ansible', 'aws', 'gcp', 'azure',
    'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'graphql', 'rest',
    'ai', 'ml', 'machine learning', 'deep learning', 'llm', 'gpt', 'openai',
    'webassembly', 'wasm', 'deno', 'bun', 'node', 'deno',
    'tailwind', 'css', 'html', 'vite', 'webpack', 'rollup', 'esbuild',
    'd3', 'threejs', 'canvas', 'webgl', 'flutter', 'react native', 'ionic',
    'github', 'gitlab', 'bitbucket', 'ci', 'cd', 'jenkins', 'github actions',
    'testing', 'jest', 'vitest', 'cypress', 'playwright', 'selenium',
    'security', 'oauth', 'jwt', 'encryption', 'blockchain', 'crypto',
    'api', 'backend', 'frontend', 'fullstack', 'devops', 'sre',
    'linux', 'windows', 'macos', 'serverless', 'edge computing'
]


@dataclass
class HNItem:
    id: int
    title: str
    url: str
    points: int
    author: str
    created_at: str
    type: str
    comment_count: int


class HackerNewsScraper:
    """Scraper for Hacker News technology posts"""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Qualtio-Tech-Radar/1.0'
        })

    def get_top_stories(self, limit: int = 50) -> List[HNItem]:
        """Get top stories from Hacker News"""
        items = []
        
        try:
            response = self.session.get(f"{self.BASE_URL}/topstories.json")
            response.raise_for_status()
            story_ids = response.json()[:limit]
            
            for story_id in story_ids:
                item = self._get_item(story_id)
                if item and item.type == 'story':
                    items.append(item)
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error fetching top stories: {e}")
            
        return items

    def search_tech_posts(self, min_points: int = 10, limit: int = 100, days_back: int = 7) -> List[HNItem]:
        """Search for technology-related posts filtered by points and date"""
        all_items = []
        
        # Calculate cutoff timestamp for date filtering
        cutoff_date = datetime.now() - timedelta(days=days_back)
        cutoff_timestamp = cutoff_date.timestamp()
        
        try:
            response = self.session.get(f"{self.BASE_URL}/topstories.json")
            response.raise_for_status()
            story_ids = response.json()
            
            for story_id in story_ids[:500]:
                item = self._get_item(story_id)
                if item and item.type == 'story':
                    # Filter by points
                    if item.points < min_points:
                        continue
                    
                    # Filter by date (check if post is within the specified days)
                    try:
                        if isinstance(item.created_at, (int, float)):
                            post_timestamp = item.created_at
                        else:
                            post_timestamp = datetime.fromisoformat(str(item.created_at)).timestamp()
                        
                        if post_timestamp < cutoff_timestamp:
                            continue
                    except (ValueError, TypeError):
                        # If we can't parse the date, include the item anyway
                        pass
                    
                    # Check if it's tech-related
                    if self._is_tech_related(item.title, item.url):
                        all_items.append(item)
                        
                if len(all_items) >= limit:
                    break
                    
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error searching tech posts: {e}")
            
        return sorted(all_items, key=lambda x: x.points, reverse=True)

    def _get_item(self, item_id: int) -> Optional[HNItem]:
        """Get a single item by ID"""
        try:
            response = self.session.get(f"{self.BASE_URL}/item/{item_id}.json")
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
                
            return HNItem(
                id=data.get('id', 0),
                title=data.get('title', ''),
                url=data.get('url', f"https://news.ycombinator.com/item?id={item_id}"),
                points=data.get('score', 0),
                author=data.get('by', ''),
                created_at=data.get('time', 0),
                type=data.get('type', 'story'),
                comment_count=data.get('descendants', 0)
            )
        except:
            return None

    def _is_tech_related(self, title: str, url: str) -> bool:
        """Check if a post is technology related"""
        text = f"{title} {url}".lower()
        
        for keyword in TECH_KEYWORDS:
            if keyword.lower() in text:
                return True
                
        return False

    def get_posts_by_keyword(self, keyword: str, limit: int = 20) -> List[HNItem]:
        """Get posts mentioning a specific keyword"""
        items = []
        
        try:
            response = self.session.get(f"{self.BASE_URL}/topstories.json")
            response.raise_for_status()
            story_ids = response.json()[:1000]
            
            for story_id in story_ids:
                item = self._get_item(story_id)
                if item and item.type == 'story':
                    if keyword.lower() in item.title.lower():
                        items.append(item)
                        
                if len(items) >= limit:
                    break
                    
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error searching by keyword: {e}")
            
        return sorted(items, key=lambda x: x.points, reverse=True)

    def get_tech_summary(self, min_points: int = 10, days_back: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """Get a summary of technology mentions by category"""
        posts = self.search_tech_posts(min_points=min_points, limit=200, days_back=days_back)
        
        categories = {
            'frontend': [],
            'backend': [],
            'ai_ml': [],
            'devops': [],
            'databases': [],
            'languages': [],
            'tools': []
        }
        
        category_keywords = {
            'frontend': ['react', 'vue', 'angular', 'svelte', 'nextjs', 'javascript', 'typescript', 'css', 'html'],
            'backend': ['api', 'server', 'backend', 'rest', 'graphql', 'node', 'express', 'fastapi'],
            'ai_ml': ['ai', 'ml', 'machine learning', 'llm', 'gpt', 'openai', 'deep learning', 'neural'],
            'devops': ['docker', 'kubernetes', 'aws', 'cloud', 'ci', 'cd', 'devops', 'infrastructure'],
            'databases': ['database', 'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'data'],
            'languages': ['python', 'rust', 'go', 'java', 'javascript', 'typescript', 'kotlin', 'swift'],
            'tools': ['github', 'git', 'tool', 'editor', 'ide', 'vscode', 'testing']
        }
        
        for post in posts:
            text = f"{post.title} {post.url}".lower()
            
            for category, keywords in category_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        categories[category].append({
                            'title': post.title,
                            'url': post.url,
                            'points': post.points,
                            'comments': post.comment_count,
                            'author': post.author
                        })
                        break
                        
        return categories


def main():
    """Test the scraper"""
    scraper = HackerNewsScraper()
    posts = scraper.get_tech_summary(min_points=10, days_back=7)
    
    for category, items in posts.items():
        print(f"\n{category.upper()}: {len(items)} posts")
        for item in items[:3]:
            print(f"  - {item['title']} ({item['points']} points)")


if __name__ == "__main__":
    main()