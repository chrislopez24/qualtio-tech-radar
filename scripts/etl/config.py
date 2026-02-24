from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class GitHubTrendingSource(BaseModel):
    enabled: bool = True
    language: str = "all"
    time_range: str = "daily"


class HackerNewsSource(BaseModel):
    enabled: bool = True
    min_points: int = 10
    days_back: int = 7


class GoogleTrendsSource(BaseModel):
    enabled: bool = True
    seed_topics: list[str] = Field(default_factory=list)


class SourcesConfig(BaseModel):
    github_trending: GitHubTrendingSource = Field(default_factory=GitHubTrendingSource)
    hackernews: HackerNewsSource = Field(default_factory=HackerNewsSource)
    google_trends: GoogleTrendsSource = Field(default_factory=GoogleTrendsSource)


class ClassificationConfig(BaseModel):
    model: str = "gpt-4"
    temperature: float = 0.2
    json_mode: bool = True


class FilteringConfig(BaseModel):
    auto_ignore: list[str] = Field(default_factory=list)
    include_only: list[str] = Field(default_factory=list)
    min_confidence: float = 0.5


class OutputConfig(BaseModel):
    public_file: str = "src/data/data.ai.json"
    internal_file: str = "src/data/data.ai.full.json"


class RateLimitConfig(BaseModel):
    requests_per_minute: int = 30
    max_retries: int = 3


class CheckpointConfig(BaseModel):
    enabled: bool = True
    interval: int = 100


class DeepScanConfig(BaseModel):
    enabled: bool = False
    repos: list[str] = Field(default_factory=list)


class ETLConfig(BaseModel):
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    filtering: FilteringConfig = Field(default_factory=FilteringConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    checkpoint: CheckpointConfig = Field(default_factory=CheckpointConfig)
    deep_scan: DeepScanConfig = Field(default_factory=DeepScanConfig)


def load_etl_config(config_path: str) -> ETLConfig:
    path = Path(config_path)
    if not path.exists():
        return ETLConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return ETLConfig(**data)