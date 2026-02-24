from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class GitHubTrendingSource(BaseModel):
    enabled: bool = True
    min_stars: int = 100
    max_repos: int = 50
    time_range: str = "daily"
    language: Optional[str] = None


class HackerNewsSource(BaseModel):
    enabled: bool = True
    min_points: int = 10
    max_posts: int = 100


class GoogleTrendsSource(BaseModel):
    enabled: bool = True
    country: str = "US"
    category: str = "tech"
    max_results: int = 50


class Sources(BaseModel):
    github_trending: GitHubTrendingSource = Field(default_factory=GitHubTrendingSource)
    hackernews: HackerNewsSource = Field(default_factory=HackerNewsSource)
    google_trends: GoogleTrendsSource = Field(default_factory=GoogleTrendsSource)


class Classification(BaseModel):
    model: str = "llama-3.3-70b"
    temperature: float = 0.3
    max_retries: int = 3
    batch_size: int = 10


class Filtering(BaseModel):
    min_confidence: float = 0.3
    min_mentions: int = 2
    exclude_keywords: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)


class RadarOutput(BaseModel):
    max_technologies: int = 50


class Output(BaseModel):
    ai_data_file: str = "src/data/data.ai.json"
    manual_data_file: str = "src/data/data.json"
    radar: RadarOutput = Field(default_factory=RadarOutput)


class RateLimit(BaseModel):
    requests_per_minute: int = 30
    retry_after: int = 60


class Checkpoint(BaseModel):
    enabled: bool = True
    file: str = ".checkpoint.json"


class DeepScan(BaseModel):
    enabled: bool = False
    max_depth: int = 3
    include_readme: bool = True


class ETLConfig(BaseModel):
    sources: Sources = Field(default_factory=Sources)
    classification: Classification = Field(default_factory=Classification)
    filtering: Filtering = Field(default_factory=Filtering)
    output: Output = Field(default_factory=Output)
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    checkpoint: Checkpoint = Field(default_factory=Checkpoint)
    deep_scan: DeepScan = Field(default_factory=DeepScan)


def load_etl_config(config_path: str) -> ETLConfig:
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return ETLConfig(**data)
    return ETLConfig()