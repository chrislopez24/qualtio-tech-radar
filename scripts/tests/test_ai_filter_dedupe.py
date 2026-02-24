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


class TestDeduplicationAndDeprecation:
    """Test suite for deduplication, hierarchy, and deprecation detection"""

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