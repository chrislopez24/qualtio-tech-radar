"""Tests for the output generator module"""

import pytest
import json
from pathlib import Path
from etl.output_generator import generate_outputs, sanitize_for_public
from etl.evidence import EvidenceRecord


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
    assert set(tech["signals"].keys()) == {"ghMomentum", "ghPopularity", "hnHeat"}
    assert "googleMomentum" not in tech["signals"]


def test_output_serializes_optional_canonical_fields_and_evidence():
    from types import SimpleNamespace
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    output = pipeline._generate_output([
        SimpleNamespace(
            name="TypeScript",
            description="Typed superset of JavaScript.",
            stars=98000,
            quadrant="languages",
            ring="adopt",
            confidence=0.95,
            trend="up",
            moved=0,
            market_score=92.2,
            signals={"gh_momentum": 90, "gh_popularity": 85, "hn_heat": 10},
            is_deprecated=False,
            replacement=None,
            canonical_id="typescript",
            entity_type="language",
            evidence=[
                EvidenceRecord(
                    source="deps_dev",
                    metric="reverse_dependents",
                    subject_id="npm:typescript",
                    raw_value=500000,
                    normalized_value=97.0,
                    observed_at="2026-03-07T00:00:00Z",
                    freshness_days=1,
                )
            ],
        )
    ])

    tech = output["technologies"][0]
    assert tech["canonicalId"] == "typescript"
    assert tech["entityType"] == "language"
    assert tech["evidence"][0]["source"] == "deps_dev"
    assert tech["evidence"][0]["subjectId"] == "npm:typescript"


def test_output_marks_item_invalid_when_source_coverage_has_no_evidence():
    from types import SimpleNamespace
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    output = pipeline._generate_output([
        SimpleNamespace(
            name="Python",
            description="Programming language",
            stars=0,
            quadrant="languages",
            ring="adopt",
            confidence=0.9,
            trend="stable",
            moved=0,
            market_score=85.0,
            signals={
                "gh_momentum": 50.0,
                "gh_popularity": 70.0,
                "hn_heat": 0.0,
                "source_coverage": 2.0,
            },
            evidence=[],
            is_deprecated=False,
            replacement=None,
        )
    ])

    tech = output["technologies"][0]
    assert tech["sourceCoverage"] == 2
    assert tech["editorialStatus"] == "invalid"
    assert "missingEvidence" in tech["editorialFlags"]


def test_sanitize_for_public_keeps_editorial_contract_fields():
    sanitized = sanitize_for_public(
        {
            "id": "python",
            "name": "Python",
            "quadrant": "languages",
            "ring": "adopt",
            "description": "Programming language",
            "moved": 0,
            "editorialStatus": "invalid",
            "editorialFlags": ["missingEvidence"],
        }
    )

    assert sanitized["editorialStatus"] == "invalid"
    assert sanitized["editorialFlags"] == ["missingEvidence"]


def test_quality_snapshot_counts_quadrant_mismatch_and_missing_evidence_as_editorially_weak():
    from etl.artifact_quality import quality_snapshot

    snapshot = quality_snapshot(
        [
            {
                "id": "pytorch",
                "name": "PyTorch",
                "quadrant": "languages",
                "ring": "trial",
                "description": "Deep learning framework",
                "marketScore": 82.3,
                "sourceCoverage": 2,
                "editorialStatus": "invalid",
                "editorialFlags": ["quadrantMismatch", "missingEvidence"],
            }
        ],
        strong_ring="trial",
    )

    assert snapshot["editoriallyWeakCount"] == 1
    assert snapshot["topSuspicious"][0]["reasons"] == ["quadrantMismatch", "missingEvidence"]
    assert snapshot["status"] == "bad"


def test_pipeline_output_propagates_semantic_suspicion_flags_into_editorial_quality():
    from types import SimpleNamespace
    from etl.pipeline import RadarPipeline
    from etl.classifier import ClassificationResult
    from etl.evidence import EvidenceRecord

    pipeline = RadarPipeline()
    item = pipeline._build_filtered_item(
        SimpleNamespace(
            stars=150000,
            market_score=82.3,
            signals={"gh_momentum": 75.0, "gh_popularity": 88.0, "hn_heat": 25.0},
            moved=0,
            sources=["github", "hackernews"],
            topics=[],
            evidence=[
                EvidenceRecord(
                    source="deps_dev",
                    metric="reverse_dependents",
                    subject_id="pypi:pytorch",
                    raw_value=250000,
                    normalized_value=94.0,
                    observed_at="2026-03-07T00:00:00Z",
                    freshness_days=1,
                )
            ],
            canonical_id=None,
            entity_type="technology",
        ),
        ClassificationResult(
            name="PyTorch",
            quadrant="languages",
            description="Deep learning framework",
            confidence=0.9,
            trend="up",
            strategic_value="high",
            suspicion_flags=["quadrant_mismatch"],
        ),
    )
    item.ring = "trial"

    output = pipeline._generate_output([item], [])

    tech = output["technologies"][0]
    assert tech["editorialStatus"] == "invalid"
    assert tech["editorialFlags"] == ["quadrantMismatch"]

    ring_quality = output["meta"]["pipeline"]["ringQuality"]["trial"]
    assert ring_quality["editoriallyWeakCount"] == 1
    assert ring_quality["status"] == "bad"
    assert ring_quality["topSuspicious"][0]["reasons"] == ["quadrantMismatch"]


def test_output_generator_generates_optional_provenance_fields(tmp_path):
    """Test that optional provenance fields are generated in public output."""
    output_dir = tmp_path / "data"
    output_dir.mkdir()

    technologies = [
        {
            "id": "go",
            "name": "Go",
            "quadrant": "platforms",
            "ring": "adopt",
            "description": "Compiled language",
            "moved": 0,
            "source_summary": "github+hn blend",
            "signal_freshness": "fresh:7d",
        }
    ]

    generate_outputs(technologies, output_dir)

    with open(output_dir / "data.ai.json") as f:
        public_payload = json.load(f)

    tech = public_payload["technologies"][0]
    assert tech["sourceSummary"] == "github+hn blend"
    assert tech["signalFreshness"] == "fresh:7d"


def test_output_generator_keeps_backward_compatibility_without_provenance_fields(tmp_path):
    """Test that provenance fields are omitted when absent."""
    output_dir = tmp_path / "data"
    output_dir.mkdir()

    technologies = [
        {
            "id": "legacy",
            "name": "Legacy",
            "quadrant": "tools",
            "ring": "assess",
            "description": "Legacy tool",
            "moved": 0,
        }
    ]

    generate_outputs(technologies, output_dir)

    with open(output_dir / "data.ai.json") as f:
        public_payload = json.load(f)

    tech = public_payload["technologies"][0]
    assert "sourceSummary" not in tech
    assert "signalFreshness" not in tech


def test_pipeline_output_includes_compact_explainability_metadata():
    from types import SimpleNamespace
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    pipeline.previous_snapshot = {
        "technologies": [
            {"id": "react", "name": "React", "ring": "trial", "marketScore": 72.5},
            {"id": "vue", "name": "Vue", "ring": "assess", "marketScore": 66.0},
        ],
        "watchlist": [],
    }
    pipeline._last_filter_stats = {
        "classified": 6,
        "qualified": 4,
        "ai_accepted": 3,
        "rejected_low_sources": 1,
        "rejected_quality_gate": 1,
        "rejected_ai_filter": 1,
    }

    output = pipeline._generate_output(
        [
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
                signals={"gh_momentum": 80, "gh_popularity": 90, "hn_heat": 60},
                is_deprecated=False,
                replacement=None,
            ),
            SimpleNamespace(
                name="Svelte",
                description="Compiler for reactive UI",
                stars=82000,
                quadrant="tools",
                ring="trial",
                confidence=0.82,
                trend="up",
                moved=2,
                market_score=79.1,
                signals={"gh_momentum": 75, "gh_popularity": 70, "hn_heat": 55},
                is_deprecated=False,
                replacement=None,
            ),
        ],
        [],
    )

    pipeline_meta = output["meta"]["pipeline"]
    assert pipeline_meta["rejectedByStage"] == {
        "insufficientSources": 1,
        "qualityGate": 1,
        "aiFilter": 1,
    }
    assert pipeline_meta["ringDistribution"] == {
        "adopt": 1,
        "trial": 1,
        "assess": 0,
        "hold": 0,
    }
    assert pipeline_meta["topAdded"] == [
        {"id": "svelte", "name": "Svelte", "ring": "trial", "marketScore": 79.1}
    ]
    assert pipeline_meta["topDropped"] == [
        {"id": "vue", "name": "Vue", "ring": "assess", "marketScore": 66.0}
    ]
    assert pipeline_meta["ringQuality"]["adopt"] == {
        "count": 1,
        "avgMarketScore": 88.4,
        "githubOnlyRatio": 0.0,
        "resourceLikeCount": 0,
        "editoriallyWeakCount": 1,
        "topSuspicious": [
            {
                "id": "react",
                "name": "React",
                "marketScore": 88.4,
                "reasons": ["missingEvidence"],
            }
        ],
        "status": "bad",
    }
    assert pipeline_meta["ringQuality"]["trial"] == {
        "count": 1,
        "avgMarketScore": 79.1,
        "githubOnlyRatio": 0.0,
        "resourceLikeCount": 0,
        "editoriallyWeakCount": 1,
        "topSuspicious": [
            {
                "id": "svelte",
                "name": "Svelte",
                "marketScore": 79.1,
                "reasons": ["missingEvidence"],
            }
        ],
        "status": "bad",
    }
    assert pipeline_meta["ringQuality"]["assess"] == {
        "count": 0,
        "avgMarketScore": 0.0,
        "githubOnlyRatio": 0.0,
        "resourceLikeCount": 0,
        "editoriallyWeakCount": 0,
        "topSuspicious": [],
        "status": "good",
    }
    assert pipeline_meta["ringQuality"]["hold"] == {
        "count": 0,
        "avgMarketScore": 0.0,
        "githubOnlyRatio": 0.0,
        "resourceLikeCount": 0,
        "editoriallyWeakCount": 0,
        "topSuspicious": [],
        "status": "good",
    }
    assert pipeline_meta["quadrantQuality"]["tools"] == {
        "count": 2,
        "avgMarketScore": 83.75,
        "githubOnlyRatio": 0.0,
        "resourceLikeCount": 0,
        "editoriallyWeakCount": 2,
        "topSuspicious": [
            {
                "id": "react",
                "name": "React",
                "marketScore": 88.4,
                "reasons": ["missingEvidence"],
            },
            {
                "id": "svelte",
                "name": "Svelte",
                "marketScore": 79.1,
                "reasons": ["missingEvidence"],
            },
        ],
        "status": "warn",
    }
    assert pipeline_meta["quadrantQuality"]["platforms"]["status"] == "missing"
    assert pipeline_meta["quadrantQuality"]["techniques"]["status"] == "missing"
    assert pipeline_meta["quadrantQuality"]["languages"]["status"] == "missing"
    assert pipeline_meta["quadrantRingQuality"]["tools"]["adopt"] == {
        "count": 1,
        "avgMarketScore": 88.4,
        "githubOnlyRatio": 0.0,
        "resourceLikeCount": 0,
        "editoriallyWeakCount": 1,
        "topSuspicious": [
            {
                "id": "react",
                "name": "React",
                "marketScore": 88.4,
                "reasons": ["missingEvidence"],
            }
        ],
        "status": "bad",
    }
    assert pipeline_meta["quadrantRingQuality"]["tools"]["trial"] == {
        "count": 1,
        "avgMarketScore": 79.1,
        "githubOnlyRatio": 0.0,
        "resourceLikeCount": 0,
        "editoriallyWeakCount": 1,
        "topSuspicious": [
            {
                "id": "svelte",
                "name": "Svelte",
                "marketScore": 79.1,
                "reasons": ["missingEvidence"],
            }
        ],
        "status": "bad",
    }
    assert pipeline_meta["quadrantRingQuality"]["platforms"]["adopt"]["status"] == "missing"


def test_pipeline_output_includes_quality_data_for_each_ring():
    from types import SimpleNamespace
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    pipeline._last_filter_stats = {
        "classified": 3,
        "qualified": 3,
        "ai_accepted": 3,
        "rejected_low_sources": 0,
        "rejected_quality_gate": 0,
        "rejected_ai_filter": 0,
    }

    output = pipeline._generate_output(
        [
            SimpleNamespace(
                name="Ohmyzsh",
                description="A framework for managing your zsh configuration.",
                stars=180000,
                quadrant="tools",
                ring="trial",
                confidence=0.8,
                trend="up",
                moved=0,
                market_score=67.0,
                signals={"gh_momentum": 96, "gh_popularity": 100, "hn_heat": 0},
                is_deprecated=False,
                replacement=None,
            ),
            SimpleNamespace(
                name="free-programming-books",
                description="Freely available programming books and learning resources.",
                stars=380000,
                quadrant="techniques",
                ring="assess",
                confidence=0.7,
                trend="stable",
                moved=0,
                market_score=58.0,
                signals={"gh_momentum": 85, "gh_popularity": 100, "hn_heat": 0},
                is_deprecated=False,
                replacement=None,
            ),
        ],
        [],
    )

    ring_quality = output["meta"]["pipeline"]["ringQuality"]

    assert ring_quality["trial"]["count"] == 1
    assert ring_quality["trial"]["githubOnlyRatio"] == 1.0
    assert ring_quality["trial"]["editoriallyWeakCount"] == 1
    assert ring_quality["trial"]["status"] == "bad"
    assert ring_quality["trial"]["topSuspicious"][0]["id"] == "ohmyzsh"
    assert "githubOnly" in ring_quality["trial"]["topSuspicious"][0]["reasons"]
    assert "editoriallyWeak" in ring_quality["trial"]["topSuspicious"][0]["reasons"]

    assert ring_quality["assess"]["count"] == 1
    assert ring_quality["assess"]["resourceLikeCount"] == 1
    assert ring_quality["assess"]["githubOnlyRatio"] == 1.0
    assert ring_quality["assess"]["status"] == "warn"

    quadrant_quality = output["meta"]["pipeline"]["quadrantQuality"]
    assert quadrant_quality["tools"]["count"] == 1
    assert quadrant_quality["tools"]["githubOnlyRatio"] == 1.0
    assert quadrant_quality["tools"]["editoriallyWeakCount"] == 1
    assert quadrant_quality["tools"]["status"] == "warn"
    assert quadrant_quality["techniques"]["count"] == 1
    assert quadrant_quality["techniques"]["resourceLikeCount"] == 1
    assert quadrant_quality["techniques"]["status"] == "warn"
    assert quadrant_quality["platforms"]["status"] == "missing"
    assert quadrant_quality["languages"]["status"] == "missing"

    quadrant_ring_quality = output["meta"]["pipeline"]["quadrantRingQuality"]
    assert quadrant_ring_quality["tools"]["trial"]["count"] == 1
    assert quadrant_ring_quality["tools"]["trial"]["githubOnlyRatio"] == 1.0
    assert quadrant_ring_quality["tools"]["trial"]["editoriallyWeakCount"] == 1
    assert quadrant_ring_quality["tools"]["trial"]["status"] == "bad"
    assert quadrant_ring_quality["techniques"]["assess"]["count"] == 1
    assert quadrant_ring_quality["techniques"]["assess"]["resourceLikeCount"] == 1
    assert quadrant_ring_quality["techniques"]["assess"]["status"] == "warn"
    assert quadrant_ring_quality["platforms"]["adopt"]["status"] == "missing"


def test_pipeline_output_flags_educational_trial_repositories_as_editorially_weak():
    from types import SimpleNamespace
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()

    output = pipeline._generate_output(
        [
            SimpleNamespace(
                name="You-Dont-Know-JS",
                description="A book series exploring JavaScript fundamentals in depth.",
                stars=190000,
                quadrant="tools",
                ring="trial",
                confidence=0.8,
                trend="up",
                moved=0,
                market_score=66.0,
                signals={"gh_momentum": 90, "gh_popularity": 95, "hn_heat": 0},
                is_deprecated=False,
                replacement=None,
            ),
        ],
        [],
    )

    ring_quality = output["meta"]["pipeline"]["ringQuality"]

    assert ring_quality["trial"]["count"] == 1
    assert ring_quality["trial"]["editoriallyWeakCount"] == 1
    assert ring_quality["trial"]["status"] == "bad"
    assert ring_quality["trial"]["topSuspicious"][0]["id"] == "you-dont-know-js"
    assert "editoriallyWeak" in ring_quality["trial"]["topSuspicious"][0]["reasons"]


def test_output_includes_evidence_summary_source_coverage_and_why_this_ring():
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
                "adoption_score": 94,
                "mindshare_score": 78,
                "health_score": 86,
                "risk_score": 88,
                "source_coverage": 4,
                "has_external_adoption": 1,
                "github_only": 0,
            },
            evidence=[
                EvidenceRecord(
                    source="deps_dev",
                    metric="reverse_dependents",
                    subject_id="npm:react",
                    raw_value=800000,
                    normalized_value=97.0,
                    observed_at="2026-03-07T00:00:00Z",
                    freshness_days=1,
                ),
                EvidenceRecord(
                    source="stackexchange",
                    metric="tag_activity",
                    subject_id="reactjs",
                    raw_value=240000,
                    normalized_value=89.0,
                    observed_at="2026-03-07T00:00:00Z",
                    freshness_days=2,
                ),
            ],
            is_deprecated=False,
            replacement=None,
        )
    ])

    tech = output["technologies"][0]
    assert tech["sourceCoverage"] == 4
    assert tech["evidenceSummary"]["hasExternalAdoption"] is True
    assert "deps_dev" in tech["evidenceSummary"]["sources"]
    assert tech["sourceFreshness"]["freshestDays"] == 1
    assert tech["sourceFreshness"]["stalestDays"] == 2
    assert tech["whyThisRing"]


def test_sanitize_for_public_normalizes_explainability_aliases_without_leaking_snake_case():
    sanitized = sanitize_for_public(
        {
            "id": "react",
            "name": "React",
            "quadrant": "tools",
            "ring": "adopt",
            "description": "UI library",
            "moved": 0,
            "source_coverage": 4,
            "source_freshness": {"freshestDays": 1, "stalestDays": 2},
            "evidence_summary": {"sources": ["github"], "metrics": [], "hasExternalAdoption": False, "githubOnly": True},
            "why_this_ring": "Because.",
        }
    )

    assert "source_coverage" not in sanitized
    assert "source_freshness" not in sanitized
    assert "evidence_summary" not in sanitized
    assert "why_this_ring" not in sanitized
    assert sanitized["sourceCoverage"] == 4
    assert sanitized["whyThisRing"] == "Because."


def test_output_evidence_summary_github_only_uses_observed_sources_not_stale_signal_flag():
    from types import SimpleNamespace
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    output = pipeline._generate_output([
        SimpleNamespace(
            name="React",
            description="UI library",
            stars=220000,
            quadrant="tools",
            ring="trial",
            confidence=0.9,
            trend="up",
            moved=0,
            market_score=78.0,
            signals={
                "gh_momentum": 90.0,
                "gh_popularity": 96.0,
                "hn_heat": 0.0,
                "github_only": 1.0,
                "has_external_adoption": 1.0,
            },
            evidence=[
                EvidenceRecord(
                    source="deps_dev",
                    metric="reverse_dependents",
                    subject_id="npm:react",
                    raw_value=700000,
                    normalized_value=98.0,
                    observed_at="2026-03-07T00:00:00Z",
                    freshness_days=1,
                )
            ],
            is_deprecated=False,
            replacement=None,
        )
    ])

    tech = output["technologies"][0]
    assert "deps_dev" in tech["evidenceSummary"]["sources"]
    assert tech["evidenceSummary"]["githubOnly"] is False
