from etl.contracts import MarketEntity
from etl.evidence import EvidenceRecord


class _DepsDevStub:
    def __init__(self):
        self.subjects = []

    def fetch(self, subjects):
        self.subjects.append(list(subjects))
        return [
            EvidenceRecord(
                source="deps_dev",
                metric="reverse_dependents",
                subject_id="npm:react",
                raw_value=42000,
                normalized_value=78.0,
                observed_at="2026-03-13T00:00:00+00:00",
                freshness_days=1,
            ),
            EvidenceRecord(
                source="deps_dev",
                metric="default_version",
                subject_id="npm:react@19.2.0",
                raw_value="19.2.0",
                normalized_value=100.0,
                observed_at="2026-03-13T00:00:00+00:00",
                freshness_days=1,
            ),
        ]


class _OSVStub:
    def __init__(self):
        self.subjects = []

    def fetch(self, subjects):
        self.subjects.append(list(subjects))
        return [
            EvidenceRecord(
                source="osv",
                metric="known_vulnerabilities",
                subject_id="npm:react@19.2.0",
                raw_value=1,
                normalized_value=20.0,
                observed_at="2026-03-13T00:00:00+00:00",
                freshness_days=1,
            )
        ]


def test_validation_enrichment_only_augments_known_mapped_entities():
    from etl.validation_enrichment import enrich_market_entities_with_validation

    entities = [
        MarketEntity(
            canonical_name="React",
            canonical_slug="react",
            editorial_kind="framework",
            topic_family="ui",
            ecosystems=["npm"],
            source_evidence=[
                {"source": "github_trending", "metric": "github_stars", "normalized_value": 86.0},
            ],
        ),
        MarketEntity(
            canonical_name="Go",
            canonical_slug="go",
            editorial_kind="language",
            topic_family="cloud",
            ecosystems=["go"],
            source_evidence=[
                {"source": "seed_catalog", "metric": "curated_presence", "normalized_value": 72.0},
            ],
        ),
    ]

    enriched = enrich_market_entities_with_validation(
        entities,
        deps_dev_source=_DepsDevStub(),
        osv_source=_OSVStub(),
    )

    react = next(entity for entity in enriched if entity.canonical_slug == "react")
    go = next(entity for entity in enriched if entity.canonical_slug == "go")

    react_metrics = {item["metric"] for item in react.source_evidence}
    go_metrics = {item["metric"] for item in go.source_evidence}

    assert {"github_stars", "reverse_dependents", "default_version", "known_vulnerabilities"} <= react_metrics
    assert go_metrics == {"curated_presence"}


def test_snapshot_builder_uses_validation_evidence_as_adoption_and_risk_modifiers():
    from etl.signals.snapshot_builder import build_market_snapshot

    baseline = MarketEntity(
        canonical_name="React",
        canonical_slug="react",
        editorial_kind="framework",
        topic_family="ui",
        source_evidence=[
            {"source": "github_trending", "metric": "github_stars", "normalized_value": 86.0},
        ],
    )
    validated = baseline.model_copy(deep=True)
    validated.source_evidence.extend(
        [
            {"source": "deps_dev", "metric": "reverse_dependents", "normalized_value": 78.0},
            {"source": "deps_dev", "metric": "default_version", "normalized_value": 100.0},
            {"source": "osv", "metric": "known_vulnerabilities", "normalized_value": 20.0},
        ]
    )

    baseline_snapshot = build_market_snapshot([baseline])[0]
    validated_snapshot = build_market_snapshot([validated])[0]

    assert validated_snapshot.adoption_signals["adoption"] >= baseline_snapshot.adoption_signals["adoption"]
    assert validated_snapshot.maturity_signals["maturity"] >= baseline_snapshot.maturity_signals["maturity"]
    assert validated_snapshot.risk_signals["risk"] > baseline_snapshot.risk_signals["risk"]
