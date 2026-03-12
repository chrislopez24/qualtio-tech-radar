import logging
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class RateLimitConfig(BaseModel):
    requests_per_minute: int = Field(ge=1, default=30)
    max_retries: int = Field(ge=1, default=3)


class GitHubTrendingSource(BaseModel):
    enabled: bool = True
    language: Literal["all", "python", "javascript", "typescript", "java", "go", "rust", "c++", "c#", "php", "ruby", "swift", "kotlin"] = "all"
    time_range: Literal["daily", "weekly", "monthly"] = "monthly"
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    @field_validator("language", "time_range", mode="before")
    @classmethod
    def string_to_lowercase(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class HackerNewsSource(BaseModel):
    enabled: bool = True
    min_points: int = Field(ge=1, default=25)
    days_back: int = Field(ge=1, default=90)


class DepsDevSource(BaseModel):
    enabled: bool = False
    base_url: str = "https://api.deps.dev"
    timeout_seconds: int = Field(ge=1, default=15)
    cache_file: str = "src/data/cache/deps_dev.json"
    cache_ttl_seconds: int = Field(ge=1, default=604800)
    negative_cache_ttl_seconds: int = Field(ge=1, default=86400)
    request_budget: int = Field(ge=1, default=12)


class StackExchangeSource(BaseModel):
    enabled: bool = False
    base_url: str = "https://api.stackexchange.com/2.3"
    site: str = "stackoverflow"
    pagesize: int = Field(ge=1, le=100, default=1)
    timeout_seconds: int = Field(ge=1, default=15)
    cache_file: str = "src/data/cache/stackexchange.json"
    cache_ttl_seconds: int = Field(ge=1, default=86400)
    negative_cache_ttl_seconds: int = Field(ge=1, default=86400)
    request_budget: int = Field(ge=1, default=25)


class PyPIStatsSource(BaseModel):
    enabled: bool = False
    base_url: str = "https://pypistats.org/api"
    period: Literal["recent", "overall"] = "recent"
    timeout_seconds: int = Field(ge=1, default=15)
    cache_file: str = "src/data/cache/pypistats.json"
    cache_ttl_seconds: int = Field(ge=1, default=86400)
    negative_cache_ttl_seconds: int = Field(ge=1, default=86400)
    request_budget: int = Field(ge=1, default=12)


class OSVSource(BaseModel):
    enabled: bool = False
    base_url: str = "https://api.osv.dev/v1"
    timeout_seconds: int = Field(ge=1, default=15)
    cache_file: str = "src/data/cache/osv.json"
    cache_ttl_seconds: int = Field(ge=1, default=604800)


class SourcesConfig(BaseModel):
    github_trending: GitHubTrendingSource = Field(default_factory=GitHubTrendingSource)
    hackernews: HackerNewsSource = Field(default_factory=HackerNewsSource)
    deps_dev: DepsDevSource = Field(default_factory=DepsDevSource)
    stackexchange: StackExchangeSource = Field(default_factory=StackExchangeSource)
    pypistats: PyPIStatsSource = Field(default_factory=PyPIStatsSource)
    osv: OSVSource = Field(default_factory=OSVSource)


class ClassificationConfig(BaseModel):
    model: str = "hf:MiniMaxAI/MiniMax-M2.5"
    temperature: float = Field(ge=0.0, le=2.0, default=0.1)
    json_mode: bool = True



class FilteringConfig(BaseModel):
    auto_ignore: list[str] = Field(default_factory=list)
    include_only: list[str] = Field(default_factory=list)
    min_confidence: float = Field(ge=0.0, le=1.0, default=0.6)
    min_sources: int = Field(ge=1, default=2)
    min_consistency_days: int = Field(ge=1, default=14)


class OutputConfig(BaseModel):
    public_file: str = "src/data/data.ai.json"


class CheckpointConfig(BaseModel):
    enabled: bool = True
    interval: int = Field(ge=1, default=100)


class ScoringWeightsConfig(BaseModel):
    # GitHub is our primary source (real adoption)
    github_momentum: float = Field(ge=0.0, default=0.60)
    github_popularity: float = Field(ge=0.0, default=0.25)
    # HN is secondary (early buzz)
    hn_heat: float = Field(ge=0.0, default=0.15)


class ScoringThresholdsConfig(BaseModel):
    adopt: float = Field(ge=0.0, le=100.0, default=80.0)
    trial: float = Field(ge=0.0, le=100.0, default=60.0)
    assess: float = Field(ge=0.0, le=100.0, default=40.0)


class HysteresisConfig(BaseModel):
    promote_delta: float = Field(ge=0.0, default=15.0)
    demote_delta: float = Field(ge=0.0, default=15.0)
    cooldown_weeks: int = Field(ge=0, default=12)


class ScoringConfig(BaseModel):
    weights: ScoringWeightsConfig = Field(default_factory=ScoringWeightsConfig)
    thresholds: ScoringThresholdsConfig = Field(default_factory=ScoringThresholdsConfig)
    hysteresis: HysteresisConfig = Field(default_factory=HysteresisConfig)


class DistributionConfig(BaseModel):
    target_total: int = Field(ge=5, default=75)
    min_per_quadrant: int = Field(ge=1, default=2)
    max_per_quadrant: int = Field(ge=1, default=20)
    min_per_ring: int = Field(ge=0, default=1)
    target_per_ring: int = Field(ge=0, default=18)
    max_per_ring: int = Field(ge=0, default=24)


class MinStarsConfig(BaseModel):
    assess: int = Field(ge=0, default=500)
    trial: int = Field(ge=0, default=2000)
    adopt: int = Field(ge=0, default=10000)


class MinHNMentionsConfig(BaseModel):
    assess: int = Field(ge=0, default=3)
    trial: int = Field(ge=0, default=10)
    adopt: int = Field(ge=0, default=25)


class QualityGatesConfig(BaseModel):
    min_stars: MinStarsConfig = Field(default_factory=MinStarsConfig)
    min_hn_mentions: MinHNMentionsConfig = Field(default_factory=MinHNMentionsConfig)
    require_production_evidence: bool = True


class HistoryConfig(BaseModel):
    enabled: bool = True
    file: str = "src/data/data.ai.history.json"
    max_weeks: int = Field(ge=1, default=24)


class DistributionGuardrailConfig(BaseModel):
    enabled: bool = True
    max_ring_ratio: float = Field(gt=0.0, le=1.0, default=0.5)


class LLMOptimizationConfig(BaseModel):
    enabled: bool = True
    max_calls_per_run: int = Field(ge=1, le=500, default=40)
    borderline_band: float = Field(ge=0.0, le=20.0, default=5.0)
    watchlist_ratio: float = Field(gt=0.0, lt=1.0, default=0.25)
    cache_enabled: bool = True
    cache_file: str = "src/data/llm_cache.json"
    cache_drift_threshold: float = Field(ge=0.0, default=3.0)


class ETLConfig(BaseModel):
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    filtering: FilteringConfig = Field(default_factory=FilteringConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    checkpoint: CheckpointConfig = Field(default_factory=CheckpointConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    distribution: DistributionConfig = Field(default_factory=DistributionConfig)
    quality_gates: QualityGatesConfig = Field(default_factory=QualityGatesConfig)
    history: HistoryConfig = Field(default_factory=HistoryConfig)
    distribution_guardrail: DistributionGuardrailConfig = Field(default_factory=DistributionGuardrailConfig)
    llm_optimization: LLMOptimizationConfig = Field(default_factory=LLMOptimizationConfig)


def load_etl_config(config_path: str) -> ETLConfig:
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Config file not found at {path}, using defaults")
        return ETLConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return ETLConfig(**data)
