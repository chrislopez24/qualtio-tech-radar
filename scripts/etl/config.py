from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class GitHubTrendingSource(BaseModel):
    enabled: bool = True
    language: Literal["all", "python", "javascript", "typescript", "java", "go", "rust", "c++", "c#", "php", "ruby", "swift", "kotlin"] = "all"
    time_range: Literal["daily", "weekly", "monthly"] = "daily"

    @field_validator("language", "time_range", mode="before")
    @classmethod
    def string_to_lowercase(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class HackerNewsSource(BaseModel):
    enabled: bool = True
    min_points: int = Field(ge=1, default=10)
    days_back: int = Field(ge=1, default=7)


class GoogleTrendsSource(BaseModel):
    enabled: bool = True
    seed_topics: list[str] = Field(default_factory=list)


class SourcesConfig(BaseModel):
    github_trending: GitHubTrendingSource = Field(default_factory=GitHubTrendingSource)
    hackernews: HackerNewsSource = Field(default_factory=HackerNewsSource)
    google_trends: GoogleTrendsSource = Field(default_factory=GoogleTrendsSource)


class ClassificationConfig(BaseModel):
    model: str = "gpt-4"
    temperature: float = Field(ge=0.0, le=2.0, default=0.2)
    json_mode: bool = True


class FilteringConfig(BaseModel):
    auto_ignore: list[str] = Field(default_factory=list)
    include_only: list[str] = Field(default_factory=list)
    min_confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class OutputConfig(BaseModel):
    public_file: str = "src/data/data.ai.json"
    internal_file: str = "src/data/data.ai.full.json"


class RateLimitConfig(BaseModel):
    requests_per_minute: int = Field(ge=1, default=30)
    max_retries: int = Field(ge=1, default=3)


class CheckpointConfig(BaseModel):
    enabled: bool = True
    interval: int = Field(ge=1, default=100)


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