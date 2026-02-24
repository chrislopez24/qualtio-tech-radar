import pytest
from dataclasses import dataclass
from unittest.mock import Mock, patch
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


class TestAITechnologyFilter:
    """Test suite for AI technology filter"""

    def test_ai_filter_removes_low_strategic_value_items(self):
        """Low strategic value items like rimraf should be filtered out"""
        items = [
            MockTechItem(name="React", description="UI Library", stars=220000),
            MockTechItem(name="rimraf", description="Node remove utility", stars=5000),
            MockTechItem(name="chalk", description="Terminal string styling", stars=12000),
            MockTechItem(name="lodash", description="Utility library", stars=56000),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        kept = AITechnologyFilter(filter_config).filter(items)
        
        assert "rimraf" not in [i.name for i in kept]

    def test_ai_filter_keeps_high_strategic_value_items(self):
        """High strategic value items should always be kept"""
        items = [
            MockTechItem(name="React", description="UI Library", stars=220000),
            MockTechItem(name="Kubernetes", description="Container orchestration", stars=105000),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        kept = AITechnologyFilter(filter_config).filter(items)
        
        assert "React" in [i.name for i in kept]
        assert "Kubernetes" in [i.name for i in kept]

    def test_auto_ignore_rules_work(self):
        """Items in auto_ignore list should be filtered out"""
        items = [
            MockTechItem(name="React", description="UI Library", stars=220000),
            MockTechItem(name="debug", description="Tiny debugging utility", stars=12000),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = ["debug", "ansi-styles", "is-odd"]
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        kept = AITechnologyFilter(filter_config).filter(items)
        
        assert "debug" not in [i.name for i in kept]
        assert "React" in [i.name for i in kept]

    def test_include_only_works(self):
        """Only items in include_only list should be kept when specified"""
        items = [
            MockTechItem(name="React", description="UI Library", stars=220000),
            MockTechItem(name="Vue", description="Progressive framework", stars=206000),
            MockTechItem(name="Angular", description="Platform for web", stars=95000),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = ["React", "Vue"]
        filter_config.min_confidence = 0.5

        kept = AITechnologyFilter(filter_config).filter(items)
        
        assert len(kept) == 2
        assert "React" in [i.name for i in kept]
        assert "Vue" in [i.name for i in kept]
        assert "Angular" not in [i.name for i in kept]

    def test_strategic_value_classification(self):
        """Items should be classified by strategic value"""
        items = [
            MockTechItem(name="React", description="UI Library", stars=220000),
            MockTechItem(name="some-random-lib", description="Small utility", stars=10),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        result = AITechnologyFilter(filter_config).filter(items)
        
        for item in result:
            assert item.strategic_value is not None
            if item.stars > 10000:
                assert item.strategic_value in [StrategicValue.HIGH, StrategicValue.MEDIUM]
            elif item.stars > 100:
                assert item.strategic_value == StrategicValue.MEDIUM
            else:
                assert item.strategic_value == StrategicValue.LOW