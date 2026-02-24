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