# Market-Signal Ring Classification Design

## Context

- Goal: make AI radar useful as an external market radar (not internal repo adoption).
- Current behavior is not useful: almost all entries end up in `adopt`.
- Root causes in current ETL:
  - GitHub source uses global star ranking (`sort=stars`) which is popularity, not trend momentum.
  - Google Trends is effectively disabled (`seed_topics: []`).
  - Ring assignment is heavily biased by stars and lacks robust temporal memory.

## Goals

1. Produce a ring distribution that reflects market momentum (`adopt/trial/assess/hold`) with clear rationale.
2. Avoid degenerate output (for example, all technologies in one ring).
3. Keep classification deterministic and auditable run-to-run.
4. Preserve weekly automation and low operational overhead.

## Non-Goals

- No migration to organization-only scanning.
- No frontend redesign.
- No hard dependency on a single model vendor for ring logic.

## Approaches Considered

### A) LLM-centric ring assignment

- Let LLM infer rings mostly from name + stats.
- Pros: fast to implement.
- Cons: opaque, unstable, hard to debug, prone to ring collapse.

### B) Percentile-only ring assignment

- Rank by one score and force fixed percentages per ring.
- Pros: guarantees distribution.
- Cons: can feel artificial when absolute signal is weak.

### C) Hybrid market signal model (recommended)

- Build deterministic multi-source market score + temporal trend, then assign rings with rule thresholds and percentile fallback.
- Pros: explainable, stable, dynamic, resistant to collapse.
- Cons: moderate implementation effort.

## Recommended Design

### 1) Source Signal Model

Use three external sources, each with explicit market semantics:

- GitHub: recency + momentum (not just total stars).
- Hacker News: discussion intensity and recurrence.
- Google Trends: search momentum over time.

Implementation direction:

- Update GitHub source to gather market-relevant candidates by recency windows (`created` and `pushed`), plus popularity context.
- Enable Google Trends with a maintained seed list.
- Keep HN quality filters but improve technology extraction to avoid noisy first-word parsing.

### 2) Canonical Tech Identity

Normalize and merge aliases before scoring:

- Canonical name map (for example `nextjs -> next.js`, `reactjs -> react`).
- Merge source records by canonical name.
- Preserve source-level evidence for explainability.

### 3) Feature Engineering

Per technology, compute normalized features (0-100):

- `gh_popularity`
- `gh_momentum` (recent growth/recency proxy)
- `hn_heat` (mentions + points quality)
- `google_momentum` (rising query strength)
- `source_diversity` (present in 1, 2, or 3 sources)
- `trend_delta` (change versus prior runs)

Composite market score:

`market_score = 0.35*gh_momentum + 0.20*gh_popularity + 0.25*hn_heat + 0.20*google_momentum`

Confidence score:

- Increases with source diversity and consistency across runs.
- Decreases for one-source spikes and ambiguous classification.

### 4) Temporal Memory and Movement

Persist weekly history to support trend and ring movement:

- Add history artifact: `src/data/data.ai.history.json` (rolling 26 weeks).
- Store per tech: `market_score`, `ring`, `quadrant`, `timestamp`.
- Compute rolling metrics: 4-week slope, volatility, and direction.

This enables meaningful `trend` and `moved` fields instead of static values.

### 5) Ring Assignment Rules

Primary rule set (absolute semantics):

- `adopt`: high score and stable momentum (mature + consistently relevant).
- `trial`: strong positive momentum, not yet stable at adopt level.
- `assess`: early/medium signal worth evaluating.
- `hold`: weak or declining signal.

Guardrails:

- Hysteresis: require minimum delta to change ring between consecutive runs.
- Cool-down: avoid flip-flop in consecutive weeks.
- Distribution sanity fallback: if one ring exceeds a max ratio (for example 65%), rebalance edge items by percentile to adjacent rings.

This keeps semantic meaning while preventing collapse to one ring.

### 6) Quadrant Assignment

Keep quadrant separate from ring and primarily deterministic:

- Rule-based classifier from language/topics/name patterns.
- LLM only as fallback for ambiguous cases.
- Persist resolved quadrant per canonical technology to reduce churn.

### 7) Explainability in Output

Each output item should include short rationale metadata:

- Top contributing signals (for example `GH momentum + HN heat`).
- Last score delta.
- Source coverage (`github/hn/google`).

This makes the radar auditable and trustworthy.

## Data Contract Changes

### `src/data/data.ai.json` (public)

Keep existing fields and add/standardize:

- `trend`: derived from temporal slope.
- `moved`: ring delta versus previous run.
- `marketScore`: 0-100.
- `signals`: compact source indicators.

### `src/data/data.ai.history.json` (new)

Rolling history snapshot used by ETL only (can be committed for reproducibility).

## Validation Strategy

1. Unit tests for scoring and ring assignment boundaries.
2. Regression tests for anti-collapse behavior (fixture should not produce all-adopt).
3. Determinism test: same input snapshot -> same output.
4. Temporal test: synthetic rising/declining sequences move rings logically.
5. End-to-end ETL dry-run and JSON schema validation.

## Success Criteria

- Ring distribution is non-degenerate and semantically coherent.
- Weekly runs show meaningful movement when market signals change.
- Same inputs produce identical outputs.
- Output rationale explains ring placement for each technology.

## Risks and Mitigations

- Risk: overreacting to weekly noise.
  - Mitigation: smoothing + hysteresis + cool-down.
- Risk: Google Trends sparsity for niche technologies.
  - Mitigation: source diversity weighting; avoid penalizing missing single source excessively.
- Risk: alias mismatch causing duplicates.
  - Mitigation: expanded canonical alias map + duplicate tests.
