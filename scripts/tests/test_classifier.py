"""Tests for the ETL classifier module"""

import pytest
from unittest.mock import patch, MagicMock
from etl.classifier import ClassificationResult, TechnologyClassifier


def test_classifier_parses_structured_json_response():
    """Test that classifier can parse JSON object responses from AI"""
    classifier = TechnologyClassifier()
    
    mock_response = '''{"name": "React", "quadrant": "platforms", "ring": "adopt", "description": "UI library", "confidence": 0.9, "trend": "up"}'''
    
    result = classifier._parse_response(mock_response, "React")
    
    assert result.quadrant in {"platforms", "techniques", "tools", "languages"}
    assert result.ring in {"adopt", "trial", "assess", "hold"}
    assert result.confidence >= 0.0
    assert result.confidence <= 1.0


def test_classifier_fallback_markdown_json():
    """Test that classifier falls back to parsing markdown fenced JSON"""
    classifier = TechnologyClassifier()
    
    markdown_response = '''
Here is the classification:

```json
{
  "name": "Rust",
  "quadrant": "languages",
  "ring": "trial",
  "description": "Systems programming language",
  "confidence": 0.85,
  "trend": "up"
}
```
'''
    
    result = classifier._parse_response(markdown_response, "Rust")
    
    assert result.quadrant == "languages"
    assert result.ring == "trial"
    assert result.confidence == 0.85


def test_classifier_invalid_json_returns_fallback():
    """Test that invalid JSON returns fallback classification"""
    classifier = TechnologyClassifier()
    
    invalid_response = "This is not JSON at all"
    
    result = classifier._parse_response(invalid_response, "TestTech")
    
    assert result.quadrant in {"platforms", "techniques", "tools", "languages"}
    assert result.name == "TestTech"


def test_classifier_validates_quadrant():
    """Test that invalid quadrant values are normalized"""
    classifier = TechnologyClassifier()
    
    response = '{"name": "Test", "quadrant": "programming", "ring": "adopt", "description": "test", "confidence": 0.5, "trend": "stable"}'
    
    result = classifier._parse_response(response, "Test")
    
    assert result.quadrant in {"platforms", "techniques", "tools", "languages"}


def test_classifier_has_rationale_field():
    """Test that classification result includes rationale"""
    classifier = TechnologyClassifier()
    
    response = '{"name": "Go", "quadrant": "languages", "ring": "adopt", "description": "Programming language", "confidence": 0.95, "trend": "stable", "rationale": "High adoption and stable community"}'
    
    result = classifier._parse_response(response, "Go")
    
    assert hasattr(result, 'rationale')


def test_classifier_schema_validation():
    """Test that classifier validates required fields"""
    classifier = TechnologyClassifier()
    
    incomplete_response = '{"name": "Test"}'
    
    result = classifier._parse_response(incomplete_response, "Test")
    
    assert result.name == "Test"
    assert result.quadrant in {"platforms", "techniques", "tools", "languages"}


def test_classifier_ring_normalization():
    """Test that ring values are normalized correctly"""
    classifier = TechnologyClassifier()
    
    response = '{"name": "Test", "quadrant": "tools", "ring": "production_ready", "description": "test", "confidence": 0.5, "trend": "up"}'
    
    result = classifier._parse_response(response, "Test")
    
    assert result.ring in {"adopt", "trial", "assess", "hold"}


def test_classifier_trend_normalization():
    """Test that trend values are normalized correctly"""
    classifier = TechnologyClassifier()
    
    response = '{"name": "Test", "quadrant": "tools", "ring": "trial", "description": "test", "confidence": 0.5, "trend": "growing"}'
    
    result = classifier._parse_response(response, "Test")
    
    assert result.trend in {"up", "down", "stable", "new"}


def test_classifier_handles_none_content_from_llm():
    """Classifier should gracefully fallback when LLM content is None"""
    classifier = TechnologyClassifier()

    result = classifier._parse_response(None, "React")  # type: ignore[arg-type]

    assert result.name == "React"
    assert result.ring in {"adopt", "trial", "assess", "hold"}


def test_classifier_logs_request_metrics():
    """Classifier should log token and size metrics for each request"""
    classifier = TechnologyClassifier(api_key="test-key")
    classifier.client = MagicMock()

    mock_message = MagicMock()
    mock_message.content = '{"name":"React","quadrant":"tools","ring":"adopt","description":"UI library","confidence":0.9,"trend":"up"}'
    mock_message.tool_calls = []

    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 120
    mock_usage.completion_tokens = 80
    mock_usage.total_tokens = 200

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    classifier.client.chat.completions.create.return_value = mock_response

    with patch("etl.classifier.logger.info") as mock_logger_info:
        classifier.classify_one("React", 220000, 10, "UI library")

    metric_logs = [
        call for call in mock_logger_info.call_args_list
        if call.args and isinstance(call.args[0], str) and "LLM classify request metrics" in call.args[0]
    ]
    assert metric_logs


def test_classifier_returns_semantic_decision_with_strategic_value():
    """Test that classifier returns strategic_value and rationale in a single LLM call"""
    from etl.classifier import TechnologyClassifier

    classifier = TechnologyClassifier(api_key="test-key")
    result = classifier._parse_response(
        '{"name":"React","quadrant":"tools","ring":"adopt","description":"UI","confidence":0.9,"trend":"up","strategic_value":"high","rationale":"Widely adopted UI library with strong community"}',
        "React",
    )
    assert hasattr(result, "rationale")
    assert hasattr(result, "confidence")
    assert hasattr(result, "strategic_value")
    assert result.strategic_value == "high"
    assert result.rationale == "Widely adopted UI library with strong community"
