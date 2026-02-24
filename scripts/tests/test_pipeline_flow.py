"""Test for complete pipeline orchestration flow"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass, field
from typing import List, Optional

from etl.config import ETLConfig, SourcesConfig, ClassificationConfig, FilteringConfig, OutputConfig


@dataclass
class MockRepository:
    name: str
    full_name: str
    description: str
    stars: int
    forks: int
    language: Optional[str]
    topics: List[str] = field(default_factory=list)
    url: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class MockHackerNewsPost:
    title: str
    points: int
    url: str


class TestPipelineFlow:
    """Test complete pipeline orchestration"""

    def test_pipeline_executes_all_phases_in_order(self):
        """Pipeline should execute all phases in correct order and produce output"""
        from etl.pipeline import RadarPipeline

        config = ETLConfig()

        with patch('etl.pipeline.GitHubScraper') as mock_github, \
             patch('etl.pipeline.HackerNewsScraper') as mock_hn, \
             patch('etl.pipeline.TechnologyClassifier') as mock_classifier, \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner') as mock_deep_scanner:

            mock_github.return_value.get_trending_repos.return_value = [
                MockRepository(
                    name="React",
                    full_name="facebook/react",
                    description="React UI library",
                    stars=220000,
                    forks=56000,
                    language="JavaScript",
                    topics=["ui", "framework"],
                    url="https://github.com/facebook/react"
                ),
                MockRepository(
                    name="Rust",
                    full_name="rust-lang/rust",
                    description="Systems programming language",
                    stars=95000,
                    forks=12000,
                    language="Rust",
                    topics=["programming-language", "systems"],
                    url="https://github.com/rust-lang/rust"
                ),
            ]

            mock_hn.return_value.search_tech_posts.return_value = [
                MockHackerNewsPost(title="Rust is amazing", points=100, url=""),
                MockHackerNewsPost(title="React 19 released", points=200, url=""),
            ]

            mock_classifier.return_value.classify_batch.return_value = [
                MockClassificationResult(name="React", quadrant="tools", ring="adopt",
                                        description="React UI library", confidence=0.9, trend="up"),
                MockClassificationResult(name="Rust", quadrant="languages", ring="adopt",
                                        description="Systems programming", confidence=0.85, trend="up"),
            ]

            mock_filter.return_value.filter.return_value = [
                MockFilteredItem(
                    name="React",
                    description="React UI library",
                    stars=220000,
                    quadrant="tools",
                    ring="adopt",
                    confidence=0.9,
                    trend="up",
                    strategic_value=MockStrategicValue.HIGH
                ),
                MockFilteredItem(
                    name="Rust",
                    description="Systems programming language",
                    stars=95000,
                    quadrant="languages",
                    ring="adopt",
                    confidence=0.85,
                    trend="up",
                    strategic_value=MockStrategicValue.HIGH
                ),
            ]

            pipeline = RadarPipeline(config=config)
            output = pipeline.run()

            assert "technologies" in output
            assert len(output["technologies"]) == 2

            mock_github.return_value.get_trending_repos.assert_called_once()
            mock_hn.return_value.search_tech_posts.assert_called_once()
            mock_classifier.return_value.classify_batch.assert_called_once()
            mock_filter.return_value.filter.assert_called_once()

    def test_pipeline_phases_execute_in_order(self):
        """Verify phases are called in the correct sequence"""
        from etl.pipeline import RadarPipeline

        config = ETLConfig()
        call_order = []

        with patch('etl.pipeline.GitHubScraper') as mock_github, \
             patch('etl.pipeline.HackerNewsScraper') as mock_hn, \
             patch('etl.pipeline.TechnologyClassifier') as mock_classifier, \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner') as mock_deep_scanner:

            mock_github.return_value.get_trending_repos.return_value = []
            mock_hn.return_value.search_tech_posts.return_value = []
            mock_classifier.return_value.classify_batch.return_value = []
            mock_filter.return_value.filter.return_value = []

            def track_call(name):
                def wrapper(*args, **kwargs):
                    call_order.append(name)
                    return [] if name == "classify_batch" else None
                return wrapper

            mock_classifier.return_value.classify_batch.side_effect = track_call("classify_batch")
            mock_filter.return_value.filter.side_effect = track_call("filter")

            pipeline = RadarPipeline(config=config)
            pipeline.run()

            assert "classify_batch" in call_order
            assert "filter" in call_order
            assert call_order.index("classify_batch") < call_order.index("filter")


@dataclass
class MockClassificationResult:
    name: str
    quadrant: str
    ring: str
    description: str
    confidence: float
    trend: str


class MockStrategicValue:
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class MockFilteredItem:
    name: str
    description: str
    stars: int
    quadrant: str
    ring: str
    confidence: float
    trend: str
    strategic_value: str
    is_deprecated: bool = False
    replacement: Optional[str] = None
    merged_names: List[str] = field(default_factory=list)