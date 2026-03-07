# Radar V2 Quality Hardening Phases

## Objective

Deliver a simple, explainable, and publishable radar artifact where:

- rings/quadrants are evidence-backed,
- editorial noise is aggressively filtered,
- external-source failures do not corrupt output quality,
- LLM usage is bounded to unresolved ambiguity only.

## Phase 1: Source Reliability Baseline (Completed)

- Keep default source set: `github_trending`, `hackernews`, `deps.dev`, `pypistats`, `osv`.
- Disable `stackexchange` in default config and CLI source list.
- Add persistent caching and deterministic source handling in ETL.
- Ensure disabled sources are not queried or recorded as active evidence providers.

## Phase 2: Editorial + Ring Quality Gates (Completed)

- Harden deterministic editorial filters for resource-like and educational noise.
- Apply low-quality `assess` removal for GitHub-only weak evidence candidates.
- Keep watchlist semantics clean by preventing `adopt` in watchlist output.
- Fix hysteresis promotion path so valid `assess -> trial` transitions are not blocked.

## Phase 3: Output Contract Quality (Completed)

- Ensure `meta.pipeline` includes:
  - `ringQuality`
  - `quadrantQuality`
  - `quadrantRingQuality`
  - source run metrics
- Keep artifact explainability fields (`sourceCoverage`, `evidenceSummary`, `whyThisRing`) aligned with actual evidence.
- Enforce review gate via `scripts/review_radar_output.py` before publish decisions.

## Phase 4: Benchmark + Governance (Completed)

- Compare generated radar against:
  - Thoughtworks Tech Radar (latest available volume)
  - Zalando Tech Radar config
- Treat overlap as sanity signal, not as hard gate.
- Keep publication control anchored to internal evidence quality and review heuristics.

## Phase 5: Next Iteration (Backlog)

1. Add optional `ossinsight` adapter for GitHub activity corroboration.
2. Add optional `ecosyste.ms` package metadata adapter for cross-ecosystem evidence.
3. Add adaptive request-budget allocator by source health per run.
4. Add periodic manual editorial review for top 10 changes and convert findings into deterministic rules.
