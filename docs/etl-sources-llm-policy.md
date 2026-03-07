# ETL External Sources and LLM Policy

## Goal

Keep the pipeline simple, deterministic-first, and explainable:

- External services provide objective evidence.
- Rules and scoring assign rings.
- LLM is used only for unresolved editorial ambiguity.

The LLM must never be the only system deciding the final `data.ai.json`.

## Definitive External Services

### Enabled by default

1. `github_trending`
- Purpose: momentum and popularity baseline.
- Use in scoring: `gh_momentum`, `gh_popularity`.

2. `hackernews`
- Purpose: early mindshare and developer discussion heat.
- Use in scoring: `hn_heat`.

3. `deps.dev`
- Purpose: reverse dependents and package lineage.
- Use in scoring: external adoption corroboration.
- Scope: only explicit canonical package mappings.

4. `pypistats`
- Purpose: Python package download pressure.
- Use in scoring: external adoption corroboration.
- Scope: only explicit canonical package mappings.

5. `osv`
- Purpose: vulnerability pressure and risk.
- Use in scoring: `risk` sub-score and evidence summary.

### Disabled by default

6. `stackexchange`
- Status: disabled due unstable shared-IP throttling in our environment.
- Re-enable only if a reliable key-backed quota path exists.

## LLM Usage Policy

### Use LLM only when all are true

1. Candidate is in the borderline bucket after deterministic scoring.
2. Candidate is not an obvious resource-like/editorially weak repository.
3. Candidate does not already have strong multi-source external corroboration.
4. Budget remains (`llm_optimization.max_calls_per_run`).

### Use deterministic fallback (no LLM) when any are true

1. Obvious educational/resource collection.
2. Editorial trial/adopt ineligibility by deterministic rules.
3. Strong evidence already available (`source_coverage >= 3`, external adoption present, high confidence).
4. LLM unavailable or budget exhausted.

## Why Not "LLM Curates Final JSON"

Generating a full final radar directly from raw source dumps via LLM is not recommended:

- Lower reproducibility across runs.
- Harder to explain ring decisions.
- More prompt drift risk and hidden regressions.
- More expensive and slower than deterministic-first filtering.

Use LLM as a narrow resolver, not as the system of record.

## Operational Checklist

1. Fetch all enabled services.
2. Build evidence and deterministic scores.
3. Apply ring policy and editorial gates.
4. Call LLM only for unresolved borderline candidates.
5. Generate `data.ai.json` with explainability fields and run metrics.
6. Run review gate before publication.
