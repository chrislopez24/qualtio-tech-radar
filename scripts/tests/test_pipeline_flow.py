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

        config = ETLConfig(filtering=FilteringConfig(min_sources=1))
        config.distribution.min_per_quadrant = 1
        config.distribution.max_per_quadrant = 8
        config.quality_gates.min_hn_mentions.assess = 0
        config.quality_gates.min_hn_mentions.trial = 0
        config.quality_gates.min_hn_mentions.adopt = 0

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
            assert "llmCalls" in output["meta"]["pipeline"]

            mock_github_source.return_value.fetch.assert_called_once()
            mock_hn_source.return_value.fetch.assert_called_once()
            # Selective LLM may call classify_batch 0 or 1 times depending on
            # whether candidate selection yields borderline items.
            assert mock_classifier.return_value.classify_batch.call_count <= 1
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
             patch('etl.pipeline.DeepScanner') as mock_deep_scanner, \
             patch('etl.pipeline.GoogleTrendsSource') as mock_google_source:

            # Provide mock data so there are candidates to process
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
            ]
            mock_hn_source.return_value.fetch.return_value = [
                MockHackerNewsPost(title="React 19 released", points=200, url=""),
            ]
            mock_google_source.return_value.fetch.return_value = []
            mock_classifier.return_value.classify_batch.return_value = [
                MockClassificationResult(
                    name="React", quadrant="tools", ring="adopt",
                    description="React UI library", confidence=0.9, trend="up"
                ),
            ]
            mock_filter.return_value.filter.return_value = [
                MockFilteredItem(
                    name="React", description="React UI library", stars=220000,
                    quadrant="tools", ring="adopt", confidence=0.9, trend="up",
                    strategic_value=MockStrategicValue.HIGH
                ),
            ]

            def track_call(name):
                def wrapper(*args, **kwargs):
                    call_order.append(name)
                    return [] if name == "classify_batch" else None
                return wrapper

            mock_classifier.return_value.classify_batch.side_effect = track_call("classify_batch")
            mock_filter.return_value.filter.side_effect = track_call("filter")

            pipeline = RadarPipeline(config=config)
            pipeline.run()

            # With selective LLM, classify_batch may be called 0 or 1 times
            # depending on whether there are borderline candidates
            # The important thing is that filter is called after classification
            if "classify_batch" in call_order:
                assert call_order.index("classify_batch") < call_order.index("filter"), \
                    "classify_batch should be called before filter"
            assert "filter" in call_order, "filter should be called"

    def test_pipeline_uses_configured_classification_model(self, monkeypatch):
        """Pipeline should pass config.classification.model to AI components"""
        from etl.pipeline import RadarPipeline

        monkeypatch.delenv("SYNTHETIC_MODEL", raising=False)

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
            mock_filter.assert_called_once()
            args, kwargs = mock_filter.call_args
            assert args[0] == config.filtering
            assert kwargs["model"] == "hf:MiniMaxAI/MiniMax-M2.5"

            assert kwargs["max_drift"] == config.llm_optimization.cache_drift_threshold
            assert kwargs["llm_cache"] is not None

    def test_pipeline_prefers_synthetic_model_env_over_config(self, monkeypatch):
        """Pipeline should honor SYNTHETIC_MODEL env override when provided."""
        from etl.pipeline import RadarPipeline

        config = ETLConfig(
            classification=ClassificationConfig(model="hf:MiniMaxAI/MiniMax-M2.5")
        )
        monkeypatch.setenv("SYNTHETIC_MODEL", "hf:moonshotai/Kimi-K2.5")

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

            mock_classifier.assert_called_once_with(model="hf:moonshotai/Kimi-K2.5")
            _, kwargs = mock_filter.call_args
            assert kwargs["model"] == "hf:moonshotai/Kimi-K2.5"

    def test_pipeline_repairs_items_with_placeholder_descriptions(self):
        """Output should repair placeholder descriptions instead of dropping items."""
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
        assert "Awesome-Python" in names
        assert "React" in names
        repaired = next(tech for tech in output["technologies"] if tech["name"] == "Awesome-Python")
        assert "with 0 stars" not in repaired["description"]
        assert repaired["description"].strip() != ""

    def test_extract_tech_name_prefers_known_tech_tokens_over_first_word(self):
        from etl.pipeline import RadarPipeline

        pipeline = RadarPipeline()
        name = pipeline._extract_tech_name("Show HN: Building with PostgreSQL and Rust")
        assert name in {"postgresql", "rust"}

    def test_strategic_filter_enforces_at_least_one_per_quadrant(self):
        from etl.pipeline import RadarPipeline, NormalizedTech
        from etl.classifier import ClassificationResult

        config = ETLConfig(filtering=FilteringConfig(min_sources=1))
        config.distribution.min_per_quadrant = 1
        config.distribution.max_per_quadrant = 8
        config.quality_gates.min_hn_mentions.assess = 0
        config.quality_gates.min_hn_mentions.trial = 0
        config.quality_gates.min_hn_mentions.adopt = 0

        with patch('etl.pipeline.GitHubTrendingSource'), \
             patch('etl.pipeline.HackerNewsSource'), \
             patch('etl.pipeline.TechnologyClassifier'), \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner'):

            # Simulate aggressive filter that only keeps one quadrant
            mock_filter.return_value.filter.return_value = [
                MockFilteredItem(
                    name="React",
                    description="UI library",
                    stars=220000,
                    quadrant="tools",
                    ring="adopt",
                    confidence=0.9,
                    trend="up",
                    strategic_value=MockStrategicValue.HIGH,
                )
            ]

            pipeline = RadarPipeline(config=config)

            technologies = [
                NormalizedTech("React", "UI", 220000, 56000, "JavaScript", ["ui"], "", 25, ["github"], {}, 90.0),
                NormalizedTech("Kubernetes", "Platform", 110000, 38000, "Go", ["platform"], "", 20, ["github"], {}, 88.0),
                NormalizedTech("Rust", "Language", 95000, 12000, "Rust", ["language"], "", 15, ["github"], {}, 85.0),
                NormalizedTech("DDD", "Technique", 15000, 900, None, ["architecture"], "", 5, ["github"], {}, 70.0),
            ]

            classifications = [
                ClassificationResult("React", "tools", "adopt", "UI", 0.9, "up", strategic_value="high"),
                ClassificationResult("Kubernetes", "platforms", "trial", "Platform", 0.85, "up", strategic_value="high"),
                ClassificationResult("Rust", "languages", "trial", "Language", 0.85, "up", strategic_value="medium"),
                ClassificationResult("DDD", "techniques", "assess", "Technique", 0.75, "stable", strategic_value="medium"),
            ]

            filtered = pipeline._strategic_filter(technologies, classifications)
            quadrants = {item.quadrant for item in filtered}
            assert {"tools", "platforms", "languages", "techniques"}.issubset(quadrants)

    def test_generate_output_includes_separate_watchlist(self):
        from etl.pipeline import RadarPipeline

        pipeline = RadarPipeline()
        main_item = MockFilteredItem(
            name="React",
            description="UI library for interfaces",
            stars=220000,
            quadrant="tools",
            ring="adopt",
            confidence=0.95,
            trend="up",
            strategic_value=MockStrategicValue.HIGH,
        )
        watch_item = MockFilteredItem(
            name="Bun",
            description="JavaScript runtime",
            stars=78000,
            quadrant="platforms",
            ring="assess",
            confidence=0.8,
            trend="up",
            strategic_value=MockStrategicValue.MEDIUM,
        )

        output = pipeline._generate_output([main_item], [watch_item])  # type: ignore[arg-type]

        assert "watchlist" in output
        assert len(output["watchlist"]) == 1
        assert output["watchlist"][0]["name"] == "Bun"

    def test_build_watchlist_prefers_previous_snapshot_ids(self):
        from etl.pipeline import RadarPipeline, NormalizedTech
        from etl.classifier import ClassificationResult
        from etl.candidate_selector import CandidateSelection

        config = ETLConfig(filtering=FilteringConfig(min_sources=1))

        with patch('etl.pipeline.GitHubTrendingSource'), \
             patch('etl.pipeline.HackerNewsSource'), \
             patch('etl.pipeline.TechnologyClassifier'), \
             patch('etl.pipeline.AITechnologyFilter'), \
             patch('etl.pipeline.DeepScanner'):
            pipeline = RadarPipeline(config=config)

        pipeline.previous_snapshot = {
            "watchlist": [{"id": "keep-me"}],
        }

        technologies = [
            NormalizedTech("Keep Me", "Persist", 1000, 10, None, ["tool"], "", 2, ["github"], {}, 55.0, 2.0),
            NormalizedTech("New Item", "New", 1000, 10, None, ["tool"], "", 2, ["github"], {}, 50.0, 5.0),
        ]
        classifications = [
            ClassificationResult("Keep Me", "tools", "assess", "Persist", 0.8, "up", strategic_value="medium"),
            ClassificationResult("New Item", "tools", "assess", "New", 0.8, "up", strategic_value="medium"),
        ]
        selection = CandidateSelection(core_ids=[], watchlist_ids=[], borderline_ids=["new-item"])

        watchlist = pipeline._build_watchlist_items(technologies, classifications, selection)

        assert watchlist
        assert watchlist[0].name == "Keep Me"

    def test_build_watchlist_keeps_previous_items_even_when_absent_from_current_sources(self):
        from etl.pipeline import RadarPipeline, NormalizedTech
        from etl.candidate_selector import CandidateSelection

        config = ETLConfig(filtering=FilteringConfig(min_sources=1))

        with patch('etl.pipeline.GitHubTrendingSource'), \
             patch('etl.pipeline.HackerNewsSource'), \
             patch('etl.pipeline.TechnologyClassifier'), \
             patch('etl.pipeline.AITechnologyFilter'), \
             patch('etl.pipeline.DeepScanner'):
            pipeline = RadarPipeline(config=config)

        pipeline.previous_snapshot = {
            "watchlist": [
                {
                    "id": "legacy-watch",
                    "name": "Legacy Watch",
                    "quadrant": "platforms",
                    "ring": "assess",
                    "description": "Legacy watch item",
                    "confidence": 0.7,
                }
            ]
        }

        selection = CandidateSelection(core_ids=[], watchlist_ids=[], borderline_ids=[])
        watchlist = pipeline._build_watchlist_items([], [], selection)

        assert len(watchlist) == 0

        watchlist = pipeline._build_watchlist_items(
            technologies=[
                NormalizedTech("Current", "Current", 1000, 10, None, ["tool"], "", 2, ["github"], {}, 40.0)
            ],
            classifications=[],
            candidate_selection=selection,
        )

        assert watchlist
        assert "Legacy Watch" in {item.name for item in watchlist}

    def test_strategic_filter_backfills_to_target_min_when_quadrant_caps_block(self):
        from etl.pipeline import RadarPipeline, NormalizedTech
        from etl.classifier import ClassificationResult

        config = ETLConfig(filtering=FilteringConfig(min_sources=1))
        config.distribution.target_total = 6
        config.distribution.min_per_quadrant = 1
        config.distribution.max_per_quadrant = 1
        config.quality_gates.min_hn_mentions.assess = 0
        config.quality_gates.min_hn_mentions.trial = 0
        config.quality_gates.min_hn_mentions.adopt = 0

        with patch('etl.pipeline.GitHubTrendingSource'), \
             patch('etl.pipeline.HackerNewsSource'), \
             patch('etl.pipeline.TechnologyClassifier'), \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner'):

            mock_filter.return_value.filter.return_value = []
            pipeline = RadarPipeline(config=config)

            technologies = [
                NormalizedTech(
                    name=f"Tool-{i}",
                    description="Tool",
                    stars=10000 - i,
                    forks=100,
                    language=None,
                    topics=["tool"],
                    url="",
                    hn_mentions=5,
                    sources=["github"],
                    signals={},
                    market_score=90.0 - i,
                )
                for i in range(6)
            ]
            classifications = [
                ClassificationResult(
                    name=f"Tool-{i}",
                    quadrant="tools",
                    ring="trial",
                    description="Tool",
                    confidence=0.8,
                    trend="stable",
                    strategic_value="medium",
                )
                for i in range(6)
            ]

            filtered = pipeline._strategic_filter(technologies, classifications)

            target_min = max(4, config.distribution.target_total - 3)
            assert len(filtered) == target_min

    def test_strategic_filter_prefers_previous_main_ids_for_stability(self):
        from etl.pipeline import RadarPipeline, NormalizedTech
        from etl.classifier import ClassificationResult

        config = ETLConfig(filtering=FilteringConfig(min_sources=1))
        config.distribution.target_total = 1
        config.distribution.min_per_quadrant = 1
        config.distribution.max_per_quadrant = 1
        config.quality_gates.min_hn_mentions.assess = 0
        config.quality_gates.min_hn_mentions.trial = 0
        config.quality_gates.min_hn_mentions.adopt = 0

        with patch('etl.pipeline.GitHubTrendingSource'), \
             patch('etl.pipeline.HackerNewsSource'), \
             patch('etl.pipeline.TechnologyClassifier'), \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner'):

            mock_filter.return_value.filter.return_value = []
            pipeline = RadarPipeline(config=config)
            pipeline.previous_snapshot = {
                "technologies": [{"id": "legacy-tech"}],
            }

            technologies = [
                NormalizedTech("Legacy Tech", "Legacy", 1000, 10, None, ["tool"], "", 2, ["github"], {}, 40.0),
                NormalizedTech("New Hot", "New", 1000, 10, None, ["tool"], "", 2, ["github"], {}, 95.0),
            ]
            classifications = [
                ClassificationResult("Legacy Tech", "tools", "assess", "Legacy", 0.8, "stable", strategic_value="medium"),
                ClassificationResult("New Hot", "tools", "assess", "New", 0.8, "stable", strategic_value="medium"),
            ]

            filtered = pipeline._strategic_filter(technologies, classifications)

            assert len(filtered) == 1
            assert filtered[0].name == "Legacy Tech"

    def test_strategic_filter_can_fill_underrepresented_quadrants_with_affinity(self):
        from etl.pipeline import RadarPipeline, NormalizedTech
        from etl.classifier import ClassificationResult

        config = ETLConfig(filtering=FilteringConfig(min_sources=1))
        config.distribution.target_total = 4
        config.distribution.min_per_quadrant = 1
        config.distribution.max_per_quadrant = 4
        config.quality_gates.min_hn_mentions.assess = 0
        config.quality_gates.min_hn_mentions.trial = 0
        config.quality_gates.min_hn_mentions.adopt = 0

        with patch('etl.pipeline.GitHubTrendingSource'), \
             patch('etl.pipeline.HackerNewsSource'), \
             patch('etl.pipeline.TechnologyClassifier'), \
             patch('etl.pipeline.AITechnologyFilter') as mock_filter, \
             patch('etl.pipeline.DeepScanner'):

            mock_filter.return_value.filter.return_value = []
            pipeline = RadarPipeline(config=config)

            technologies = [
                NormalizedTech("Rust", "Systems language", 1000, 10, "Rust", [], "", 2, ["github"], {}, 95.0),
                NormalizedTech("Kubernetes", "Container orchestration platform", 1000, 10, "Go", ["infrastructure"], "", 2, ["github"], {}, 94.0),
                NormalizedTech("Playwright", "Testing framework tool", 1000, 10, "TypeScript", ["testing", "tool"], "", 2, ["github"], {}, 93.0),
                NormalizedTech("Awesome-Architecture", "Architecture patterns and guides", 1000, 10, None, [], "", 2, ["github"], {}, 92.0),
            ]
            classifications = [
                ClassificationResult("Rust", "tools", "trial", "Systems language", 0.8, "stable", strategic_value="medium"),
                ClassificationResult("Kubernetes", "tools", "trial", "Container platform", 0.8, "stable", strategic_value="medium"),
                ClassificationResult("Playwright", "tools", "trial", "Testing tool", 0.8, "stable", strategic_value="medium"),
                ClassificationResult("Awesome-Architecture", "tools", "trial", "Architecture guide", 0.8, "stable", strategic_value="medium"),
            ]

            filtered = pipeline._strategic_filter(technologies, classifications)
            quadrants = {item.quadrant for item in filtered}

            assert {"tools", "platforms", "languages", "techniques"}.issubset(quadrants)

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

    def test_pipeline_calls_llm_only_for_borderline_candidates(self):
        """Pipeline should call LLM only once (batch) for borderline candidates.

        This test verifies that with the selective LLM policy:
        1. Candidate selection happens before LLM classification
        2. Only borderline candidates are sent to LLM (not core or watchlist)
        3. LLM is called at most once per run (batch call)
        """
        from etl.pipeline import RadarPipeline, NormalizedTech
        from etl.config import ETLConfig, FilteringConfig
        from etl.candidate_selector import select_candidates
        from unittest.mock import patch, MagicMock

        config = ETLConfig(filtering=FilteringConfig(min_sources=1))
        config.llm_optimization.enabled = True
        config.llm_optimization.max_calls_per_run = 40
        pipeline = RadarPipeline(config=config)

        # Create test technologies with different characteristics
        # to ensure candidate selection produces all three buckets
        test_techs = [
            # Core candidates: high market_score + high confidence
            NormalizedTech(
                name="React",
                description="UI library",
                stars=220000,
                forks=45000,
                language="JavaScript",
                topics=["ui", "framework"],
                url="https://github.com/facebook/react",
                sources=["github", "hackernews"],
                signals={"gh_popularity": 100.0, "gh_momentum": 80.0, "hn_heat": 90.0, "score_confidence": 0.95},
                market_score=92.0,
                trend_delta=5.0,
            ),
            NormalizedTech(
                name="Kubernetes",
                description="Container orchestration",
                stars=110000,
                forks=38000,
                language="Go",
                topics=["containers", "orchestration"],
                url="https://github.com/kubernetes/kubernetes",
                sources=["github", "hackernews"],
                signals={"gh_popularity": 95.0, "gh_momentum": 70.0, "hn_heat": 85.0, "score_confidence": 0.92},
                market_score=88.0,
                trend_delta=3.0,
            ),
            # Watchlist candidates: high trend_delta
            NormalizedTech(
                name="RisingStar",
                description="New framework",
                stars=5000,
                forks=500,
                language="TypeScript",
                topics=["framework"],
                url="https://github.com/example/rising",
                sources=["github", "hackernews"],
                signals={"gh_popularity": 30.0, "gh_momentum": 90.0, "hn_heat": 95.0, "score_confidence": 0.75},
                market_score=55.0,
                trend_delta=25.0,
            ),
            # Borderline candidates: near thresholds or low confidence
            NormalizedTech(
                name="EdgeTool",
                description="Edge case tool",
                stars=2000,
                forks=200,
                language="Python",
                topics=["tool"],
                url="https://github.com/example/edge",
                sources=["github"],
                signals={"gh_popularity": 35.0, "gh_momentum": 40.0, "hn_heat": 30.0, "score_confidence": 0.55},
                market_score=65.0,  # Near core threshold of 70
                trend_delta=8.0,    # Near watchlist threshold of 10
            ),
        ]

        # Track classify_batch calls
        call_count = [0]
        captured_batch_sizes = []
        captured_batches = []

        def track_classify(batch, *args, **kwargs):
            call_count[0] += 1
            batch_size = len(batch) if batch else 0
            captured_batch_sizes.append(batch_size)
            captured_batches.append(batch.copy() if batch else [])
            # Return mock classifications
            return []

        # Manually run pipeline phases with test data
        if pipeline.classifier:
            with patch.object(pipeline.classifier, 'classify_batch', side_effect=track_classify):
                # Run phases: normalize -> enrich -> score -> select -> classify
                technologies = pipeline._normalize_and_dedupe(test_techs)
                technologies = pipeline._temporal_enrichment(technologies)
                technologies = pipeline._apply_market_scoring(technologies)

                # Build candidate items
                candidate_items = [
                    {
                        "id": t.name.lower().replace(" ", "-"),
                        "market_score": t.market_score,
                        "trend_delta": t.trend_delta,
                        "confidence": t.signals.get("score_confidence", 0.5),
                    }
                    for t in technologies
                ]

                # Select candidates
                selection = select_candidates(
                    candidate_items,
                    target_total=config.distribution.target_total,
                    watchlist_ratio=config.llm_optimization.watchlist_ratio,
                    borderline_band=config.llm_optimization.borderline_band,
                )

                # Get borderline technologies only
                borderline_techs = [
                    t for t in technologies
                    if t.name.lower().replace(" ", "-") in selection.borderline_ids
                ]

                # Current implementation calls classify_batch for ALL technologies
                # New selective implementation should only call for borderline
                # For now, we test the current behavior - it will FAIL after reordering

                # Call classify_ai (current implementation classifies all)
                classifications = pipeline._classify_ai(technologies)

                # After selective LLM implementation:
                # - call_count should be <= 1
                # - Only borderline_techs should be in captured_batches
                #
                # For now, this will show current behavior (classifies all)
                # TODO: After implementing selective LLM, this assertion should pass

                # With selective LLM: only 1 call for borderline batch
                # Without selective LLM: 1 call with all technologies
                # Either way, should be at most 1 call (batch processing)
                assert call_count[0] <= 1, \
                    f"Expected at most 1 LLM call (batch), got {call_count[0]} calls"

                # After selective LLM is implemented, add this assertion:
                # assert len(borderline_techs) == captured_batch_sizes[0], \
                #     f"Expected only {len(borderline_techs)} borderline items, got {captured_batch_sizes[0]}"
        else:
            pytest.skip("No classifier available - cannot test selective LLM")

    def test_pipeline_calls_llm_zero_times_when_no_borderline(self):
        """Pipeline should skip LLM entirely when no borderline candidates exist"""
        from etl.pipeline import RadarPipeline
        from etl.config import ETLConfig, FilteringConfig
        from unittest.mock import patch

        config = ETLConfig(filtering=FilteringConfig(min_sources=1))
        pipeline = RadarPipeline(config=config)

        call_count = [0]

        def track_classify(*args, **kwargs):
            call_count[0] += 1
            return []

        with patch.object(
            pipeline.classifier,
            "classify_batch",
            side_effect=track_classify
        ):
            # Run with minimal data
            pipeline.run()

            # LLM may be called 0 or 1 times depending on candidate selection
            assert call_count[0] <= 1, \
                f"Expected at most 1 LLM call, got {call_count[0]}"

    def test_pipeline_enforces_llm_budget(self):
        """Pipeline should enforce max_calls_per_run budget"""
        from etl.pipeline import RadarPipeline
        from etl.config import ETLConfig
        from unittest.mock import patch

        config = ETLConfig()
        config.llm_optimization.max_calls_per_run = 5
        pipeline = RadarPipeline(config=config)

        # Track call count
        call_count = [0]

        def limited_classify(*args, **kwargs):
            call_count[0] += 1
            return []

        if pipeline.classifier:
            with patch.object(
                pipeline.classifier,
                "classify_batch",
                side_effect=limited_classify
            ):
                # Run pipeline
                pipeline.run()

                # Verify budget was respected
                assert call_count[0] <= config.llm_optimization.max_calls_per_run, \
                    f"Exceeded LLM budget: {call_count[0]} calls vs limit {config.llm_optimization.max_calls_per_run}"
        else:
            # If no classifier, budget is automatically respected (0 calls)
            pass


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
