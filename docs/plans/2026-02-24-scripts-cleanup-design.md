# Scripts Cleanup Design (Aggressive)

## Context

- Branch policy: execute directly on `master` (no worktrees).
- Current ETL local run is functional and produces `src/data/data.ai.json`, but runtime is long and output quality is inconsistent for some items.
- Observed issue: placeholder descriptions such as `"<name> - technology with 0 stars"` should never appear in final output.
- Codebase currently has mixed legacy and ETL modules under `scripts/`, with overlapping responsibilities:
  - `scripts/etl/*` (new ETL package)
  - `scripts/ai/*` and `scripts/scraper/*` (legacy paths)

## Goals

1. Keep a single output file: `src/data/data.ai.json`.
2. Ensure output quality: exclude entries without a trustworthy, real description.
3. Remove dead code/files and consolidate ETL logic under `scripts/etl/`.
4. Improve observability and maintainability without breaking CLI/workflow usage.

## Non-Goals

- No frontend changes.
- No new data sources.
- No model-provider migration beyond unifying existing Synthetic OpenAI-compatible usage.

## Architecture Decisions

### 1) Single Output Contract

- `scripts/main.py` and ETL flow will generate only `src/data/data.ai.json`.
- `data.ai.full.json` generation will be removed.
- Tests and workflow steps must align to single-output behavior.

### 2) Description Quality Gate (Hard Filter)

- Add a strict description-quality validator in ETL post-classification / pre-output.
- If an item description is placeholder, empty, or synthetic filler, exclude item.
- Initial blocked patterns include:
  - `- technology with <N> stars`
  - blank/whitespace-only
  - known generic placeholders (`unknown`, `n/a`, etc.)
- Policy approved: if no reliable description exists, the item is dropped.

### 3) Module Consolidation

- `scripts/etl/pipeline.py` must use ETL-native modules only (no legacy imports from `scripts/ai/*` or legacy scraper modules unless explicitly retained wrappers are required).
- Consolidate classifier and source calls into `scripts/etl/*`.
- Remove dead legacy files after references and tests are updated.

### 4) LLM Invocation Consistency

- Normalize LLM call style to a single internal path in ETL.
- Keep model ids with explicit `hf:` prefix and configurable via ETL config/env.
- Harden parsing when model returns no content (`None`) to prevent `.strip()` crashes.
- Keep structured output handling resilient (accept JSON mode when available, fallback parse otherwise).

### 5) Observability

- Keep phase-level logs and add counters for data-quality drops.
- Desired phase metrics include:
  - collected count
  - classified count
  - filtered count
  - dropped_bad_description count
  - final output count

## Target Structure

Primary active implementation surface under:

- `scripts/main.py`
- `scripts/etl/config.py`
- `scripts/etl/pipeline.py`
- `scripts/etl/classifier.py`
- `scripts/etl/ai_filter.py`
- `scripts/etl/sources/*`
- `scripts/tests/*`

Legacy paths (`scripts/ai/*`, `scripts/scraper/*`) should be removed or reduced to minimal compatibility stubs only if required by remaining tests.

## Testing Strategy

1. Add failing tests first for:
   - placeholder-description exclusion
   - single-output generation (no full file)
   - ETL pipeline import/use of ETL classifier path
2. Run targeted ETL test suites after each step.
3. Run local ETL smoke command and validate `src/data/data.ai.json`.
4. Verify no placeholder descriptions exist in output payload.

## Success Criteria

- Only `src/data/data.ai.json` is produced by ETL CLI.
- No entries in output contain placeholder descriptions like `"technology with 0 stars"`.
- Pipeline no longer depends on legacy modules as active runtime path.
- Relevant ETL tests pass and local run completes with valid JSON.

## Risks and Mitigations

- Risk: aggressive file cleanup may break hidden imports.
  - Mitigation: remove files only after reference search + tests pass.
- Risk: stricter quality filter may reduce output count significantly.
  - Mitigation: log drop reasons and counts; adjust patterns with evidence.
- Risk: workflow mismatch with local behavior.
  - Mitigation: sync workflow commands and output expectations to single-file contract.
