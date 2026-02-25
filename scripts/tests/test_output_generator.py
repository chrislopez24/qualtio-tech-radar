"""Tests for the output generator module"""

import pytest
import json
from pathlib import Path
from etl.output_generator import generate_outputs, sanitize_for_public


@pytest.fixture
def sample_technologies():
    return [
        {
            "id": "react",
            "name": "React",
            "quadrant": "tools",
            "ring": "adopt",
            "description": "A JavaScript library for building user interfaces",
            "moved": 0,
            "trend": "up",
            "githubStars": 220000,
            "hnMentions": 150,
            "confidence": 0.95,
            "updatedAt": "2025-02-24T00:00:00Z",
            "repoNames": ["facebook/react", "reactjs/react"],
        },
        {
            "id": "rust",
            "name": "Rust",
            "quadrant": "languages",
            "ring": "trial",
            "description": "A language empowering everyone to build reliable and efficient software",
            "moved": 1,
            "trend": "up",
            "githubStars": 95000,
            "hnMentions": 75,
            "confidence": 0.88,
            "updatedAt": "2025-02-24T00:00:00Z",
            "repoNames": ["rust-lang/rust"],
        },
    ]


def test_output_generator_creates_sanitized_public_file(tmp_path, sample_technologies):
    """Test that generate_outputs creates a public file without repo_names"""
    output_dir = tmp_path / "data"
    output_dir.mkdir()

    generate_outputs(sample_technologies, output_dir)

    public_file = output_dir / "data.ai.json"
    assert public_file.exists(), "Public file should be created"

    with open(public_file) as f:
        public_payload = json.load(f)

    assert "technologies" in public_payload
    for tech in public_payload["technologies"]:
        assert "repoNames" not in tech, "repoNames should be removed from public output"


def test_output_generator_does_not_create_internal_file(tmp_path, sample_technologies):
    """Test that generate_outputs only creates the public file"""
    output_dir = tmp_path / "data"
    output_dir.mkdir()

    generate_outputs(sample_technologies, output_dir)

    full_file = output_dir / "data.ai.full.json"
    assert not full_file.exists(), "Internal full file should not be created"


def test_sanitize_for_public_removes_internal_fields(tmp_path):
    """Test that sanitize_for_public removes sensitive/internal fields"""
    tech = {
        "id": "react",
        "name": "React",
        "quadrant": "tools",
        "ring": "adopt",
        "description": "A JavaScript library",
        "moved": 0,
        "repoNames": ["facebook/react"],
        "internalNote": "secret",
    }

    sanitized = sanitize_for_public(tech)

    assert "repoNames" not in sanitized
    assert "internalNote" not in sanitized
    assert sanitized["name"] == "React"
    assert sanitized["id"] == "react"


def test_output_generator_preserves_core_fields(tmp_path, sample_technologies):
    """Test that core fields are preserved in public output"""
    output_dir = tmp_path / "data"
    output_dir.mkdir()

    generate_outputs(sample_technologies, output_dir)

    public_file = output_dir / "data.ai.json"
    with open(public_file) as f:
        public_payload = json.load(f)

    for tech in public_payload["technologies"]:
        assert "id" in tech
        assert "name" in tech
        assert "quadrant" in tech
        assert "ring" in tech
        assert "description" in tech
        assert "moved" in tech


def test_output_contains_market_score_trend_and_moved():
    from types import SimpleNamespace
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    output = pipeline._generate_output([
        SimpleNamespace(
            name="React",
            description="UI library for interfaces",
            stars=220000,
            quadrant="tools",
            ring="adopt",
            confidence=0.95,
            trend="up",
            moved=1,
            market_score=88.4,
            signals={
                "gh_momentum": 80,
                "gh_popularity": 90,
                "hn_heat": 60,
                "google_momentum": 70,
            },
            is_deprecated=False,
            replacement=None,
        )
    ])

    assert "technologies" in output
    tech = output["technologies"][0]
    assert "marketScore" in tech
    assert "trend" in tech
    assert "moved" in tech
    assert "signals" in tech
