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

    def test_ai_evaluate_uses_max_tokens_8000(self):
        """AI strategic evaluation should request a larger token budget"""
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        filter_instance = AITechnologyFilter(filter_config, model="hf:MiniMaxAI/MiniMax-M2.5")
        mock_client = Mock()

        mock_message = Mock()
        mock_message.content = '{"strategic_value": "high", "reason": "widely adopted"}'
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response = Mock()
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_response
        filter_instance._client = mock_client

        result = filter_instance._ai_evaluate("React", 220000, "UI library")

        assert result == StrategicValue.HIGH
        assert mock_client.chat.completions.create.call_args.kwargs["max_tokens"] == 8000

    def test_ai_filter_logs_request_metrics(self):
        """AI filter should log token and size metrics for each request"""
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        filter_instance = AITechnologyFilter(filter_config, model="hf:MiniMaxAI/MiniMax-M2.5")
        mock_client = Mock()

        mock_message = Mock()
        mock_message.content = '{"strategic_value": "high", "reason": "widely adopted"}'
        mock_message.tool_calls = []
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_usage = Mock()
        mock_usage.prompt_tokens = 50
        mock_usage.completion_tokens = 40
        mock_usage.total_tokens = 90

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client.chat.completions.create.return_value = mock_response
        filter_instance._client = mock_client

        with patch("etl.ai_filter.logger.info") as mock_logger_info:
            result = filter_instance._ai_evaluate("React", 220000, "UI library")

        assert result == StrategicValue.HIGH
        metric_logs = [
            call for call in mock_logger_info.call_args_list
            if call.args and isinstance(call.args[0], str) and "LLM filter request metrics" in call.args[0]
        ]
        assert metric_logs

    def test_ai_filter_uses_strategic_value_from_classifier(self):
        """AI filter should use strategic_value from classifier when available (single-pass)"""
        @dataclass
        class MockTechItemWithStrategicValue:
            name: str
            description: str = ""
            stars: int = 0
            quadrant: str = "tools"
            ring: str = "trial"
            confidence: float = 0.5
            trend: str = "stable"
            strategic_value: str = "medium"

        items = [
            MockTechItemWithStrategicValue(name="React", description="UI Library", stars=220000, strategic_value="high"),
            MockTechItemWithStrategicValue(name="rimraf", description="Node utility", stars=5000, strategic_value="low"),
            MockTechItemWithStrategicValue(name="Kubernetes", description="Container orchestration", stars=105000, strategic_value="high"),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        filter_instance = AITechnologyFilter(filter_config)
        # Set _client to None to ensure no LLM calls are made
        filter_instance._client = None

        kept = filter_instance.filter(items)
        
        # Should keep items with HIGH strategic value
        assert "React" in [i.name for i in kept]
        assert "Kubernetes" in [i.name for i in kept]
        # Should filter out items with LOW strategic value
        assert "rimraf" not in [i.name for i in kept]
        # Verify no LLM calls were made (single-pass optimization)
        assert filter_instance.metrics["calls"] == 0

    def test_ai_filter_skips_llm_when_strategic_value_present(self):
        """AI filter should skip LLM call when item already has strategic_value"""
        items = [
            MockTechItem(name="React", description="UI Library", stars=220000, strategic_value=StrategicValue.HIGH),
            MockTechItem(name="Angular", description="Framework", stars=95000, strategic_value=StrategicValue.MEDIUM),
        ]
        
        filter_config = Mock()
        filter_config.auto_ignore = []
        filter_config.include_only = []
        filter_config.min_confidence = 0.5

        filter_instance = AITechnologyFilter(filter_config)
        # _client is already None by default since SYNTHETIC_API_KEY env var not set

        kept = filter_instance.filter(items)
        
        # Verify no LLM calls were made
        assert filter_instance.metrics["calls"] == 0
        # Verify strategic values were preserved
        react_item = next((i for i in kept if i.name == "React"), None)
        angular_item = next((i for i in kept if i.name == "Angular"), None)
        assert react_item is not None
        assert angular_item is not None
        assert react_item.strategic_value == StrategicValue.HIGH
        assert angular_item.strategic_value == StrategicValue.MEDIUM
