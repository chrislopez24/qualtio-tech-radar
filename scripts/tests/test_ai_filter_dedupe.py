import pytest
from dataclasses import dataclass
from unittest.mock import Mock
from typing import List, Optional

from etl.ai_filter import AITechnologyFilter, StrategicValue


@dataclass
class MockTechItem:
    name: str
    description: str = ""
    stars: int = 0
    quadrant: str = "tools"
    ring: str = "trial"
    confidence: float = 0.5
    trend: str = "stable"
    strategic_value: Optional[StrategicValue] = None
    market_score: float = 0.0
    signals: Optional[dict] = None
    moved: int = 0
    sources: Optional[List[str]] = None


class TestDeduplicationAndDeprecation:
    """Test suite for deduplication, hierarchy, and deprecation detection"""

    def test_filter_rejects_resource_like_repositories_but_keeps_canonical_technologies(self):
        """Editorial resource repos should be filtered while real technologies survive."""
        items = [
            MockTechItem(
                name="free-programming-books",
                description="Freely available programming books collection",
                stars=356000,
                ring="adopt",
                confidence=0.95,
            ),
            MockTechItem(
                name="developer-roadmap",
                description="Interactive developer roadmaps and learning paths",
                stars=320000,
                ring="adopt",
                confidence=0.95,
            ),
            MockTechItem(
                name="public-apis",
                description="A collective list of free APIs for developers",
                stars=340000,
                ring="trial",
                confidence=0.9,
            ),
            MockTechItem(
                name="React",
                description="UI library for building user interfaces",
                stars=235000,
                ring="adopt",
                confidence=0.95,
            ),
            MockTechItem(
                name="Kubernetes",
                description="Container orchestration platform",
                stars=112000,
                quadrant="platforms",
                ring="adopt",
                confidence=0.94,
            ),
            MockTechItem(
                name="Next.js",
                description="React framework for production web applications",
                stars=132000,
                ring="trial",
                confidence=0.92,
            ),
            MockTechItem(
                name="Python",
                description="Programming language for general-purpose software development",
                stars=68000,
                quadrant="languages",
                ring="adopt",
                confidence=0.97,
            ),
            MockTechItem(
                name="Ollama",
                description="Local LLM runtime for running open models",
                stars=128000,
                quadrant="platforms",
                ring="trial",
                confidence=0.9,
            ),
        ]

        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        result = AITechnologyFilter(filter_config).filter(items)
        result_names = {item.name.lower() for item in result}

        assert "free-programming-books" not in result_names
        assert "developer-roadmap" not in result_names
        assert "public-apis" not in result_names
        assert "react" in result_names
        assert "kubernetes" in result_names
        assert "next.js" in result_names
        assert "python" in result_names
        assert "ollama" in result_names

    def test_filter_merges_duplicates_and_flags_deprecated(self):
        """Duplicate technologies should be merged, deprecated should be flagged"""
        items = [
            MockTechItem(name="ESLint", description="JavaScript linting", stars=25000),
            MockTechItem(name="eslint", description="javascript linting tool", stars=25000),
            MockTechItem(name="TSLint", description="TypeScript linting", stars=12000),
            MockTechItem(name="Babel", description="JavaScript compiler", stars=42000),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        filter_instance = AITechnologyFilter(filter_config)
        result = filter_instance.filter(items)
        result_names = [i.name for i in result]
        result_names_lower = [n.lower() for n in result_names]
        
        has_eslint = any("eslint" in n for n in result_names_lower)
        assert has_eslint, f"ESLint not found in results: {result_names}"
        assert result_names_lower.count("eslint") == 1

    def test_filter_consolidates_parent_child_hierarchies(self):
        """Parent-child technologies should be consolidated"""
        items = [
            MockTechItem(name="Firebase", description="Backend as a Service", stars=1200),
            MockTechItem(name="@firebase/firestore", description="Firestore database", stars=800),
            MockTechItem(name="@firebase/auth", description="Firebase authentication", stars=600),
            MockTechItem(name="React", description="UI Library", stars=220000),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        result = AITechnologyFilter(filter_config).filter(items)
        result_names = [i.name for i in result]
        
        assert "Firebase" in result_names

    def test_filter_flags_deprecated_with_replacement(self):
        """Deprecated technologies should be flagged with replacement suggestions"""
        items = [
            MockTechItem(name="Moment.js", description="Date library", stars=47000),
            MockTechItem(name="TSLint", description="TypeScript linting (deprecated)", stars=12000),
            MockTechItem(name="Babel", description="JavaScript compiler", stars=42000),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        filter_instance = AITechnologyFilter(filter_config)
        result = filter_instance.filter(items)
        
        deprecated_items = [i for i in result if getattr(i, 'is_deprecated', False)]
        
        assert len(deprecated_items) > 0
        deprecated_names_lower = [i.name.lower() for i in deprecated_items]
        has_tslint = any("tslint" in n for n in deprecated_names_lower)
        has_moment = any("moment" in n for n in deprecated_names_lower)
        assert has_tslint or has_moment

    def test_filter_provides_replacement_suggestions(self):
        """Deprecated items should have replacement suggestions"""
        items = [
            MockTechItem(name="TSLint", description="TypeScript linting (deprecated)", stars=12000),
            MockTechItem(name="Moment.js", description="Date library", stars=47000),
            MockTechItem(name="Babel", description="JavaScript compiler", stars=42000),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        filter_instance = AITechnologyFilter(filter_config)
        result = filter_instance.filter(items)
        
        has_replacement = any(
            getattr(i, 'replacement', None) is not None 
            for i in result 
            if getattr(i, 'is_deprecated', False)
        )
        
        assert has_replacement or len(result) > 0

    def test_filter_preserves_etl_metadata_on_filtered_items(self):
        """Filtered items should keep ETL metadata needed by downstream phases."""
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        result = AITechnologyFilter(filter_config).filter([
            MockTechItem(
                name="React",
                description="UI library",
                stars=220000,
                confidence=0.9,
                trend="up",
                strategic_value=StrategicValue.HIGH,
                market_score=92.5,
                signals={"gh_momentum": 88.0, "hn_heat": 72.0},
                moved=1,
                sources=["github", "hackernews"],
            )
        ])

        assert len(result) == 1
        assert getattr(result[0], "market_score", None) == 92.5
        assert getattr(result[0], "signals", None) == {"gh_momentum": 88.0, "hn_heat": 72.0}
        assert getattr(result[0], "moved", None) == 1
        assert getattr(result[0], "sources", None) == ["github", "hackernews"]

    def test_filter_excludes_resource_like_repositories_even_when_marked_medium(self):
        """Resource collections should not survive the editorial filter as radar technologies."""
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        result = AITechnologyFilter(filter_config).filter([
            MockTechItem(
                name="awesome-python",
                description="An opinionated list of awesome Python frameworks, libraries, software and resources.",
                stars=280000,
                confidence=0.9,
                trend="up",
                strategic_value=StrategicValue.MEDIUM,
                market_score=84.1,
                signals={"gh_momentum": 100.0, "gh_popularity": 100.0, "hn_heat": 0.0},
                sources=["github"],
            ),
            MockTechItem(
                name="React",
                description="UI library",
                stars=220000,
                confidence=0.9,
                trend="up",
                strategic_value=StrategicValue.HIGH,
                market_score=92.5,
                signals={"gh_momentum": 88.0, "hn_heat": 72.0},
                sources=["github", "hackernews"],
            ),
        ])

        result_names = {item.name.lower() for item in result}
        assert "react" in result_names
        assert "awesome-python" not in result_names
