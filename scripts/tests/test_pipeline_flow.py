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


@dataclass
class MockTechnologySignal:
    name: str
    source: str
    signal_type: str
    score: float
    raw_data: dict


class TestPipelineFlow:
    """Test complete pipeline orchestration"""

    def test_pipeline_uses_etl_classifier_module(self):
        """Pipeline should use the ETL classifier implementation"""
        from etl import pipeline

        assert pipeline.TechnologyClassifier.__module__ == "etl.classifier"

    def test_pipeline_executes_all_phases_in_order(self):
        """Pipeline should execute all phases in correct order and produce output"""
        from etl.pipeline import RadarPipeline

        config = ETLConfig()

        with patch('etl.pipeline.GitHubTrendingSource') as mock_github_source, \
             patch('etl.pipeline.HackerNewsSource') as mock_hn_source, \
             patch('etl.pipeline.TechnologyClassifier') as mock_classifier, \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner') as mock_deep_scanner:

            mock_github_source.return_value.fetch.return_value = [
                MockTechnologySignal(
                    name="React",
                    source="github_trending",
                    signal_type="github_stars",
                    score=10.0,
                    raw_data={
                        "name": "React",
                        "full_name": "facebook/react",
                        "description": "React UI library",
                        "stars": 220000,
                        "forks": 56000,
                        "language": "JavaScript",
                        "topics": ["ui", "framework"],
                        "url": "https://github.com/facebook/react",
                    },
                ),
                MockTechnologySignal(
                    name="Rust",
                    source="github_trending",
                    signal_type="github_stars",
                    score=9.5,
                    raw_data={
                        "name": "Rust",
                        "full_name": "rust-lang/rust",
                        "description": "Systems programming language",
                        "stars": 95000,
                        "forks": 12000,
                        "language": "Rust",
                        "topics": ["programming-language", "systems"],
                        "url": "https://github.com/rust-lang/rust",
                    },
                ),
            ]

            mock_hn_source.return_value.fetch.return_value = [
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

            mock_github_source.return_value.fetch.assert_called_once()
            mock_hn_source.return_value.fetch.assert_called_once()
            mock_classifier.return_value.classify_batch.assert_called_once()
            mock_filter.return_value.filter.assert_called_once()

    def test_pipeline_phases_execute_in_order(self):
        """Verify phases are called in the correct sequence"""
        from etl.pipeline import RadarPipeline

        config = ETLConfig()
        call_order = []

        with patch('etl.pipeline.GitHubTrendingSource') as mock_github_source, \
             patch('etl.pipeline.HackerNewsSource') as mock_hn_source, \
             patch('etl.pipeline.TechnologyClassifier') as mock_classifier, \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner') as mock_deep_scanner:

            mock_github_source.return_value.fetch.return_value = []
            mock_hn_source.return_value.fetch.return_value = []
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

    def test_pipeline_uses_configured_classification_model(self):
        """Pipeline should pass config.classification.model to AI components"""
        from etl.pipeline import RadarPipeline

        config = ETLConfig(
            classification=ClassificationConfig(model="hf:MiniMaxAI/MiniMax-M2.5")
        )

        with patch('etl.pipeline.GitHubTrendingSource') as mock_github_source, \
             patch('etl.pipeline.HackerNewsSource') as mock_hn_source, \
             patch('etl.pipeline.TechnologyClassifier') as mock_classifier, \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner'):

            mock_github_source.return_value.fetch.return_value = []
            mock_hn_source.return_value.fetch.return_value = []
            mock_classifier.return_value.classify_batch.return_value = []
            mock_filter.return_value.filter.return_value = []

            pipeline = RadarPipeline(config=config)
            pipeline.run()

            mock_classifier.assert_called_once_with(model="hf:MiniMaxAI/MiniMax-M2.5")
            mock_filter.assert_called_once_with(config.filtering, model="hf:MiniMaxAI/MiniMax-M2.5")

    def test_pipeline_drops_items_with_placeholder_descriptions(self):
        """Output should exclude placeholder descriptions"""
        from etl.pipeline import RadarPipeline

        config = ETLConfig()

        with patch('etl.pipeline.GitHubTrendingSource'), \
             patch('etl.pipeline.HackerNewsSource'), \
             patch('etl.pipeline.TechnologyClassifier'), \
             patch('etl.pipeline.AITechnologyFilter'), \
             patch('etl.pipeline.DeepScanner'):

            pipeline = RadarPipeline(config=config)

        output = pipeline._generate_output([  # type: ignore[arg-type]
            MockFilteredItem(
                name="Awesome-Python",
                description="awesome-python - technology with 0 stars",
                stars=284399,
                quadrant="tools",
                ring="hold",
                confidence=0.5,
                trend="stable",
                strategic_value=MockStrategicValue.MEDIUM,
            ),
            MockFilteredItem(
                name="React",
                description="UI library for building interfaces",
                stars=220000,
                quadrant="tools",
                ring="adopt",
                confidence=0.95,
                trend="up",
                strategic_value=MockStrategicValue.HIGH,
            ),
        ])

        names = [tech["name"] for tech in output["technologies"]]
        assert "Awesome-Python" not in names
        assert "React" in names

    def test_extract_tech_name_prefers_known_tech_tokens_over_first_word(self):
        from etl.pipeline import RadarPipeline

        pipeline = RadarPipeline()
        name = pipeline._extract_tech_name("Show HN: Building with PostgreSQL and Rust")
        assert name in {"postgresql", "rust"}

    def test_pipeline_collects_google_trends_when_enabled(self):
        from etl.pipeline import RadarPipeline
        from etl.config import ETLConfig

        config = ETLConfig()
        config.sources.google_trends.enabled = True
        config.sources.google_trends.seed_topics = ["ai", "devops"]

        with patch("etl.pipeline.GoogleTrendsSource") as mock_google_source:
            mock_google_source.return_value.fetch.return_value = []
            pipeline = RadarPipeline(config=config)
            technologies = pipeline._collect_sources()

        assert isinstance(technologies, list)
        mock_google_source.return_value.fetch.assert_called_once()

    def test_strategic_filter_passes_classifier_strategic_value_to_filter_items(self):
        from etl.pipeline import RadarPipeline, NormalizedTech
        from etl.classifier import ClassificationResult

        config = ETLConfig()

        with patch('etl.pipeline.GitHubTrendingSource'), \
             patch('etl.pipeline.HackerNewsSource'), \
             patch('etl.pipeline.TechnologyClassifier'), \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner'):

            captured = {}

            def capture_items(items):
                captured['items'] = items
                return []

            mock_filter.return_value.filter.side_effect = capture_items

            pipeline = RadarPipeline(config=config)

            tech = NormalizedTech(
                name='React',
                description='UI library',
                stars=220000,
                forks=56000,
                language='JavaScript',
                topics=['ui', 'framework'],
                url='https://github.com/facebook/react',
                hn_mentions=100,
                sources=['github', 'hackernews'],
                signals={'gh_popularity': 100.0, 'gh_momentum': 100.0, 'hn_heat': 80.0},
                market_score=92.0,
            )

            classification = ClassificationResult(
                name='React',
                quadrant='tools',
                ring='adopt',
                description='UI library',
                confidence=0.9,
                trend='up',
                strategic_value='high',
            )

            pipeline._strategic_filter([tech], [classification])

            assert 'items' in captured
            assert len(captured['items']) == 1
            assert getattr(captured['items'][0], 'strategic_value') == 'high'


@dataclass
class MockClassificationResult:
    name: str
    quadrant: str
    ring: str
    description: str
    confidence: float
    trend: str
    strategic_value: str = "medium"


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
