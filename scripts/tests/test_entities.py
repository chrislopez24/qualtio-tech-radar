from etl.entities import CanonicalTechnology
from etl.evidence import EvidenceRecord


def test_canonical_technology_tracks_aliases_packages_and_repos():
    entity = CanonicalTechnology(
        id="typescript",
        display_name="TypeScript",
        entity_type="technology",
        aliases={"ts", "typescript"},
        repos={"microsoft/typescript"},
        packages={"npm:typescript"},
        ecosystems={"npm"},
    )

    assert "ts" in entity.aliases
    assert "npm:typescript" in entity.packages


def test_evidence_record_captures_source_metric_and_freshness():
    record = EvidenceRecord(
        source="deps_dev",
        metric="reverse_dependents",
        subject_id="npm:react",
        raw_value=12345,
        normalized_value=92.1,
        observed_at="2026-03-07T00:00:00Z",
        freshness_days=1,
    )

    assert record.source == "deps_dev"
    assert record.normalized_value == 92.1
