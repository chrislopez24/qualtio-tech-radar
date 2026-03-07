from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from etl.config import ETLConfig
from etl.sources.deps_dev import DepsDevSource
from etl.sources.github_trending import GitHubTrendingSource
from etl.sources.hackernews import HackerNewsSource
from etl.sources.osv_source import OSVSource
from etl.sources.pypistats import PyPIStatsSource
from etl.sources.stackexchange import StackExchangeSource


@dataclass
class SourceRegistry:
    github_trending: GitHubTrendingSource
    hackernews: HackerNewsSource
    deps_dev: DepsDevSource
    stackexchange: StackExchangeSource
    pypistats: PyPIStatsSource
    osv: OSVSource

    def as_dict(self) -> dict[str, Any]:
        return {
            "github_trending": self.github_trending,
            "hackernews": self.hackernews,
            "deps_dev": self.deps_dev,
            "stackexchange": self.stackexchange,
            "pypistats": self.pypistats,
            "osv": self.osv,
        }

    def get(self, name: str) -> Any:
        return self.as_dict()[name]


def build_source_registry(
    config: ETLConfig,
    *,
    github_cls: type[GitHubTrendingSource] = GitHubTrendingSource,
    hackernews_cls: type[HackerNewsSource] = HackerNewsSource,
    deps_dev_cls: type[DepsDevSource] = DepsDevSource,
    stackexchange_cls: type[StackExchangeSource] = StackExchangeSource,
    pypistats_cls: type[PyPIStatsSource] = PyPIStatsSource,
    osv_cls: type[OSVSource] = OSVSource,
) -> SourceRegistry:
    return SourceRegistry(
        github_trending=github_cls(config.sources.github_trending),
        hackernews=hackernews_cls(config.sources.hackernews),
        deps_dev=deps_dev_cls(config.sources.deps_dev),
        stackexchange=stackexchange_cls(config.sources.stackexchange),
        pypistats=pypistats_cls(config.sources.pypistats),
        osv=osv_cls(config.sources.osv),
    )
