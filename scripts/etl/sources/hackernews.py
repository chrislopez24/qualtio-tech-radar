from datetime import datetime, timedelta
from typing import Iterator, Optional
from dataclasses import dataclass
import requests

from etl.config import HackerNewsSource as HackerNewsConfig


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
    'linux', 'windows', 'macos', 'serverless', 'edge computing',
    'neural', 'transformer', 'bert', 'gpt-4', 'claude', 'gemini',
    'supabase', 'prisma', 'drizzle', 'trpc', 'tRPC',
    'rust', 'cargo', 'actix', 'tokio',
    'golang', 'fiber', 'gin',
    'django', 'flask', 'fastapi', ' Tornado',
    'spring', 'nestjs', 'express', 'koa', 'hapi',
    'rabbitmq', 'kafka', 'nats', 'sqs',
    's3', 'cloudfront', 'route53', 'lambda', 'ec2', 'rds',
    'terraform', 'cloudformation', 'pulumi', 'cdk',
    'prometheus', 'grafana', 'elk', 'splunk',
    'grpc', 'protobuf', 'thrift', 'avro',
    'maven', 'gradle', 'npm', 'yarn', 'pnpm',
    'vim', 'emacs', 'vscode', 'intellij', 'pycharm',
]


TECH_DOMAINS = [
    'github.com', 'gitlab.com', 'bitbucket.org',
    'stackoverflow.com', 'dev.to', 'medium.com',
    'npmjs.com', 'pypi.org', 'crates.io',
    'docs.rs', 'godoc.org',
]


@dataclass
class HackerNewsItem:
    id: int
    title: str
    url: str
    points: int
    author: str
    created_at: float
    comment_count: int
    tech_score: float = 0.0


class HackerNewsAPI:
    """Hacker News API client"""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Qualtio-Tech-Radar/1.0'
        })

    def fetch_stories(self, limit: int = 500) -> list[HackerNewsItem]:
        """Fetch stories from HN API"""
        items = []
        
        try:
            response = self.session.get(f"{self.BASE_URL}/topstories.json", timeout=10)
            response.raise_for_status()
            story_ids = response.json()[:limit]
            
            for story_id in story_ids:
                item = self._fetch_item(story_id)
                if item:
                    items.append(item)
                    
        except Exception as e:
            print(f"Error fetching stories: {e}")
            
        return items

    def _fetch_item(self, item_id: int) -> Optional[HackerNewsItem]:
        """Fetch a single item by ID"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/item/{item_id}.json", 
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if not data or data.get('type') != 'story':
                return None
                
            return HackerNewsItem(
                id=data.get('id', 0),
                title=data.get('title', ''),
                url=data.get('url', f"https://news.ycombinator.com/item?id={item_id}"),
                points=data.get('score', 0),
                author=data.get('by', ''),
                created_at=float(data.get('time', 0)),
                comment_count=data.get('descendants', 0)
            )
        except Exception:
            return None


class HackerNewsSource:
    """Hacker News source with quality filters"""

    def __init__(
        self, 
        config: HackerNewsConfig,
        max_stories_scan: int = 500
    ):
        self.config = config
        self.api = HackerNewsAPI()
        self.max_stories_scan = max_stories_scan
        
    def fetch(self) -> Iterator[HackerNewsItem]:
        """Fetch and filter HN stories"""
        stories = self.api.fetch_stories(limit=self.max_stories_scan)
        
        cutoff_timestamp = (
            datetime.now() - timedelta(days=self.config.days_back)
        ).timestamp()
        
        for story in stories:
            if story.points < self.config.min_points:
                continue
                
            if story.created_at < cutoff_timestamp:
                continue
                
            tech_score = self._calculate_tech_score(story)
            if tech_score < 2.0:
                continue
                
            story.tech_score = tech_score
            yield story

    def _calculate_tech_score(self, item: HackerNewsItem) -> float:
        """Calculate tech relevance score for an item"""
        score = 0.0
        text = f"{item.title} {item.url}".lower()
        
        for keyword in TECH_KEYWORDS:
            if keyword.lower() in text:
                score += 1.0
                
        url_lower = item.url.lower()
        for domain in TECH_DOMAINS:
            if domain in url_lower:
                score += 2.0
                
        if any(tech in text for tech in ['react', 'vue', 'angular', 'svelte']):
            score += 1.5
            
        if any(ai_term in text for ai_term in ['ai', 'ml', 'llm', 'gpt', 'machine learning']):
            score += 1.5
            
        if any(devops in text for devops in ['docker', 'kubernetes', 'aws', 'cloud']):
            score += 1.0
            
        return score