# LLM Call Reduction Design

## Context

- Current ETL can perform up to two LLM calls per technology candidate:
  - AI classification in `scripts/etl/pipeline.py` via `TechnologyClassifier`.
  - Strategic-value filtering in `scripts/etl/ai_filter.py` via `_ai_evaluate`.
- The current checkpoint state shows high candidate volume (`.checkpoint/radar.json` with cursor near 174), so per-item AI calls scale quickly.
- Ring assignment and market scoring are already deterministic later in the pipeline (`scripts/etl/market_scoring.py`, `scripts/etl/ring_assignment.py`), which means part of the first LLM call is redundant.
- Product intent is clear: prioritize technologies that are currently used and sector-leading, while still keeping a focused watchlist for fast-growing technologies.

## Goals

1. Reduce LLM calls per run by at least 70%.
2. Preserve output quality for the main radar (adoption + relevance).
3. Preserve early-signal coverage through a dedicated growth watchlist.
4. Keep behavior deterministic, explainable, and safe to roll out.

## Non-Goals

- No frontend changes.
- No replacement of source ingestion architecture.
- No mandatory vendor/model migration.

## Approaches Considered

### A) Deterministic-first funnel with selective LLM (recommended)

- Apply deterministic quality and scoring filters before any LLM call.
- Call LLM only for shortlist and uncertainty/borderline items.
- Pros: largest call reduction, clearer behavior, straightforward to validate.
- Cons: requires pipeline reordering and uncertainty policy.

### B) Cache LLM decisions across runs

- Persist and reuse prior decisions when item signals have not changed materially.
- Pros: strong reduction in repeated quarterly runs.
- Cons: requires cache invalidation rules to avoid stale decisions.

### C) Model cascade by uncertainty

- Use lightweight model first, escalate uncertain cases to stronger model.
- Pros: additional cost savings when call count is still high.
- Cons: operational complexity and tuning overhead.

## Recommended Direction

Adopt **A + B** in the first iteration, reserve **C** as a phase-2 optimization.

## Proposed Architecture

### 1) Deterministic funnel before LLM

Reorder candidate flow so deterministic logic handles the full set first:

1. collect sources
2. normalize and dedupe
3. deterministic market score
4. deterministic ring assignment
5. deterministic quality gates (`min_sources`, stars/HN thresholds, confidence floor)
6. candidate selection (Core + Watchlist + Borderline)
7. selective LLM pass only for candidates requiring semantic judgment
8. output generation

This removes most low-value LLM calls from the pipeline.

### 2) Two-lane output strategy

- **Core Radar lane**: technologies with strong current adoption and stable relevance.
- **Watchlist lane**: technologies with high recent momentum/trend delta but lower maturity.

Suggested quota policy:

- Core: 70-80% of final set
- Watchlist: 20-30% of final set

This preserves "what is used now" while still surfacing "what is growing".

### 3) LLM trigger policy

Only call LLM when at least one condition is true:

- candidate is near ring threshold (borderline)
- signals are contradictory (high momentum, low source diversity, etc.)
- item is in Watchlist and requires semantic relevance validation
- deterministic confidence below configured threshold

Skip LLM for clear high-confidence deterministic decisions.

### 4) Single semantic LLM pass per selected item

Replace double semantic calls (`classifier` + `ai_filter`) with one call that returns:

- quadrant (if ambiguous)
- strategic value label
- concise rationale
- cleaned description

Ring remains deterministic from market scoring/ring engine.

### 5) LLM cache with drift-aware invalidation

Cache key should include:

- canonical name
- model id
- prompt version
- rounded signal features bucket

Reuse cache if drift is below threshold; invalidate on:

- prompt/model change
- significant signal drift
- explicit cache version bump

### 6) Quality guardrails and fallback

- If post-filter quality metrics drop below floor in-run, increase LLM budget dynamically.
- If guardrail still fails, fallback to baseline behavior for that run.
- Quality is prioritized over savings.

## Data Flow (high level)

```text
raw signals -> deterministic score/ring -> candidate lanes -> selective semantic LLM -> output
```

## Error Handling

- LLM timeout/error: fallback to deterministic decision and mark `semanticEnrichment: false`.
- Cache read error: continue without cache; never block run.
- Cache write error: log warning only.
- Budget exhaustion: prioritize unresolved borderline cases by uncertainty score.

## Testing and Validation Strategy

### Functional tests

- Deterministic candidate selector returns expected Core/Watchlist split.
- LLM trigger policy skips clear candidates and includes borderline ones.
- Cache hit/miss behavior respects drift thresholds.

### Regression tests

- For fixed fixture input, optimized output remains within quality thresholds versus baseline.
- No ring collapse and no empty radar under normal source availability.

### Shadow-run tests

Run baseline and optimized paths on same input and compare:

- Core overlap
- leader coverage
- watchlist recall
- LLM call reduction

## Success Criteria (approved)

- LLM call reduction: >= 70%
- Core overlap vs baseline: >= 85%
- Leader coverage (top adopted technologies): 100% in top-5
- Watchlist recall for top growth candidates: >= 80%
- Stable quarterly behavior with explicit watchlist representation

## Risks and Mitigations

- Risk: deterministic gates become too aggressive and remove relevant items.
  - Mitigation: uncertainty escalation + dynamic LLM budget bump.
- Risk: cache staleness degrades semantic quality.
  - Mitigation: drift thresholds + prompt/model version keying.
- Risk: overfitting to current thresholds.
  - Mitigation: shadow-run evaluation and threshold calibration before rollout.

## Rollout Plan

1. Implement deterministic candidate selector and selective LLM trigger.
2. Enable shadow-run comparison metrics.
3. Validate against success criteria over 2-3 runs.
4. Enable optimized mode as default.
5. Add optional model cascade as phase-2 if needed.
