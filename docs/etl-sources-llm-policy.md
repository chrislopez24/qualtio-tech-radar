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

4. `osv`
- Purpose: vulnerability pressure and risk.
- Use in scoring: `risk` sub-score and evidence summary.

## API Limits and Keys

Reference posture for this repository:

1. `github_trending`
- Key: optional but strongly recommended (`GH_TOKEN`).
- Why: authenticated GitHub API has much higher quota than anonymous requests.

2. `hackernews`
- Key: not required.
- Notes: public Firebase-style API; keep request volume low and cache aggressively.

3. `deps.dev`
- Key: not required.
- Notes: use canonical package mappings and persistent cache to avoid wasted calls.

4. `osv`
- Key: not required.
- Notes: prefer batched lookups from already-resolved package/version evidence.

1. `ossinsight` (public API)
- Use for: repository-level GitHub activity and trend corroboration.
- Benefit: no auth required for base usage and explicit per-IP limits.

2. `ecosyste.ms` (`packages` + related APIs)
- Use for: cross-ecosystem package metadata and dependency context.
- Benefit: open API surface aligned with package-centric evidence design.

3. Keep `libraries.io` optional
- We do not depend on `libraries.io` for core scoring.
- If account/API access is unavailable, pipeline quality remains intact with current sources.

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

## LLM Invocation Contract

Deterministic pipeline remains authoritative. LLM is called only on unresolved borderline candidates and only after all enabled external sources have been collected, cached, and scored.

Current optimization principles:

1. Load discovery evidence first (`github`, `hn`), then validation evidence (`deps.dev`, `osv`).
2. Apply deterministic editorial/quality gates.
3. Send only residual ambiguity to LLM (bounded by budget).
4. Never allow LLM-only candidates into strong rings without corroborating evidence.

## GitHub-Only Assess Policy

To keep output realistic without over-pruning:

1. `adopt`/`trial` still require corroborated evidence (no GitHub-only strong rings).
2. A narrow `assess` soft-band is allowed for mono-source GitHub candidates only if:
   - editorially plausible,
   - clearly above a minimum market-score floor,
   - strong repository scale supports sector relevance.
3. Educational/resource/style-guide/activation repositories remain blocked by editorial rules.

See also: `docs/external-sources-rate-limits-2026-03-07.md` for concrete API limits/access references.

## Operational Checklist

1. Fetch all enabled services.
2. Build evidence and deterministic scores.
3. Apply ring policy and editorial gates.
4. Call LLM only for unresolved borderline candidates.
5. Generate `data.ai.json` with explainability fields and run metrics.
6. Run review gate before publication.
