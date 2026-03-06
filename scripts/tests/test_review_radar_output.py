import json
from pathlib import Path


def test_review_summary_includes_required_sections(tmp_path):
    from review_radar_output import build_review_summary, validate_review_summary

    payload = {
        "updatedAt": "2026-03-06T12:00:00Z",
        "technologies": [
            {
                "id": "react",
                "name": "React",
                "quadrant": "tools",
                "ring": "adopt",
                "trend": "up",
                "marketScore": 91.4,
                "description": "UI library",
                "signals": {"ghMomentum": 92, "ghPopularity": 95, "hnHeat": 70},
            },
            {
                "id": "bun",
                "name": "Bun",
                "quadrant": "platforms",
                "ring": "adopt",
                "trend": "up",
                "marketScore": 52.0,
                "description": "Runtime",
                "signals": {"ghMomentum": 52, "ghPopularity": 0, "hnHeat": 0},
            },
        ],
        "watchlist": [
            {
                "id": "htmx",
                "name": "HTMX",
                "quadrant": "tools",
                "ring": "assess",
                "trend": "up",
                "marketScore": 61.0,
                "description": "Hypermedia UI approach",
                "signals": {"ghMomentum": 40, "ghPopularity": 55, "hnHeat": 12},
            }
        ],
        "meta": {
            "pipeline": {
                "repairedDescriptions": 2,
                "topAdded": [{"id": "bun", "name": "Bun", "ring": "adopt", "marketScore": 52.0}],
                "topDropped": [{"id": "vue", "name": "Vue", "ring": "assess", "marketScore": 66.0}],
                "ringDistribution": {"adopt": 2, "trial": 0, "assess": 0, "hold": 0},
            },
            "shadowGate": {
                "status": "warn",
            },
        },
    }

    summary = build_review_summary(payload, input_name="data.ai.json")
    errors = validate_review_summary(summary)

    assert errors == []
    assert summary["inputFile"] == "data.ai.json"
    assert summary["shadowStatus"] == "warn"
    assert summary["counts"] == {"technologies": 2, "watchlist": 1}
    assert summary["topTechnologies"][0]["id"] == "react"
    assert summary["newlyAdded"][0]["id"] == "bun"
    assert summary["dropped"][0]["id"] == "vue"
    assert summary["ringDistribution"]["adopt"] == 2
    assert summary["suspiciousItems"]["repairedDescriptions"] == 2
    assert summary["suspiciousItems"]["lowSignalStrongRings"][0]["id"] == "bun"
    assert summary["suspiciousItems"]["singleWeakSignal"][0]["id"] == "bun"


def test_review_summary_validation_flags_missing_sections():
    from review_radar_output import validate_review_summary

    errors = validate_review_summary({"counts": {"technologies": 0, "watchlist": 0}})

    assert "missing: topTechnologies" in errors
    assert "missing: suspiciousItems" in errors


def test_review_cli_writes_json_and_markdown_reports(tmp_path):
    import subprocess
    import sys

    input_path = tmp_path / "data.ai.json"
    json_out = tmp_path / "review-summary.json"
    md_out = tmp_path / "review-summary.md"

    input_path.write_text(
        json.dumps(
            {
                "updatedAt": "2026-03-06T12:00:00Z",
                "technologies": [],
                "watchlist": [],
                "meta": {"pipeline": {}, "shadowGate": {"status": "pass"}},
            }
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/review_radar_output.py",
            "--input",
            str(input_path),
            "--output-json",
            str(json_out),
            "--output-md",
            str(md_out),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert json_out.exists()
    assert md_out.exists()
