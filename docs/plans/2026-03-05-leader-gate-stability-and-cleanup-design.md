# Leader Gate Stability + Workflow Decoupling Design

## Context

Current GitHub Actions flow can fail on shadow evaluation (`leader_coverage`) due to run-to-run volatility. This can block downstream deploy behavior even when frontend-only iterations should still ship with the last validated `data.ai.json`.

## Goals

1. Keep quality bar strict for leaders (do not relax `leader_coverage` threshold lightly).
2. Reduce false failures from one-off noise by adding temporal inertia.
3. Decouple ETL validation from frontend deploy so frontend changes can ship on GitHub Pages using last validated data.
4. Improve code quality/maintainability in ETL/workflow and frontend.

## Non-goals

- Lowering core gate thresholds as first-line solution.
- Forcing model/base URL changes in Synthetic integration.
- Blocking frontend-only updates because ETL candidate output failed shadow evaluation.

## Decision Summary

- **Policy mode:** Stability-first with strict thresholds.
- **Leader change inertia:** require **3 consecutive runs** before leader set change is promoted.
- **Workflow behavior on ETL gate fail:** keep using the existing validated `src/data/data.ai.json`; allow frontend deploy/build path to proceed independently.

## Design

### 1) Strict gate with temporal inertia for leaders

Introduce persistent baseline state for leader tracking:

- `stable_leaders`: current approved leader set.
- `candidate_changes`: per leader change candidate:
  - `change_type` (`added`/`removed`)
  - `consecutive_count`
  - `first_seen_run`
  - `last_seen_run`
- `last_approved_run_id`
- `baseline_version`

#### Evaluation rules

1. Compute observed leaders for current run.
2. Diff observed leaders vs `stable_leaders`.
3. For each diff item:
   - if same candidate repeats from previous run, increment `consecutive_count`.
   - else initialize/reset candidate with count 1.
4. Promote candidate change only when `consecutive_count >= 3`.
5. If candidate misses one run, reset candidate count.
6. Evaluate `leader_coverage` against strict threshold using `stable_leaders` policy context.

Outcome:
- real sustained changes are accepted,
- transient one-run noise does not churn the leader set.

### 2) Workflow decoupling (ETL gate vs frontend delivery)

#### Target behavior

- ETL shadow eval can fail independently.
- Frontend deploy/build remains possible using **last validated** `src/data/data.ai.json`.
- GitHub Pages can still update for frontend-only work.

#### Job strategy

Split responsibilities:

- `update-data` (candidate ETL run + artifacts)
- `quality-gate` (shadow eval status)
- `build-frontend` (uses repo data file; not hard-blocked by candidate ETL fail)
- `deploy-pages` (allowed for frontend updates; data source remains validated file if ETL candidate not approved)

In fail/warn cases, do **not** overwrite validated data artifact used for production deploy.

### 3) Gate statuses and operational outputs

Standardize statuses:

- `PASS`: all required metrics satisfy thresholds.
- `WARN`: leader candidate drift detected but not yet sustained (count < 3).
- `FAIL`: true quality degradation or policy breach.

Extend `shadow_eval.json` with:

- `gate_status`
- `leader_transition_summary`
- `candidate_changes`
- `missing_ids` / `added_ids`
- `next_action`

This makes CI outcomes auditable and easy to reason about.

### 4) Baseline source strategy

Use robust baseline source for comparison:

- compare against **last approved stable baseline**,
- not merely previous raw run output when noisy.

This aligns with strict quality + anti-volatility objective.

### 5) Cleanup plan (“codigo top”) in two phases

#### Phase A: ETL + workflow cleanup

- Refactor shadow eval policy logic into explicit modules/functions.
- Centralize threshold/policy constants and config schema.
- Remove duplicated metric/diff formatting logic.
- Add focused tests for:
  - 3-run promotion
  - candidate reset on interruption
  - stable baseline selection
  - fail/warn/pass mapping
- Tighten workflow YAML readability (job boundaries, conditions, naming).

#### Phase B: Frontend cleanup

- Reduce component-level state/derived duplication.
- Extract shared formatting/utils for detail/watchlist rendering.
- Improve typing for optional metadata rendering paths.
- Expand targeted tests for fallback and status badges.
- Keep behavior unchanged while improving maintainability.

## Testing and Verification

### ETL / policy

- `python3 -m pytest scripts/tests -q`
- Add new tests for candidate tracking/promotion logic.

### Frontend

- `npm run lint`
- `npm test`
- `npm run build`

### Workflow-level checks

- Run workflow dispatch and verify:
  - ETL fail does not force invalid data publish,
  - frontend build/deploy path remains usable,
  - approved data file remains source of truth on failure.

## Risks and Mitigations

- **Risk:** accidental promotion of unstable leader changes.
  - **Mitigation:** explicit 3-run counter tests and reset tests.
- **Risk:** workflow condition mistakes causing unexpected deploy blocks.
  - **Mitigation:** simplify conditions, add clear status outputs, dry-run validation.
- **Risk:** coupling regression where failed ETL still mutates validated data.
  - **Mitigation:** explicit guarded write/publish step only on `PASS`.

## Rollout

1. Implement policy state + tests.
2. Implement workflow decoupling.
3. Run full local matrix.
4. Dispatch workflow, inspect artifacts/logs.
5. Iterate cleanup phase A then B with no behavior regressions.

## Acceptance Criteria

- Leader threshold remains strict.
- Leader set changes only after 3 consecutive supporting runs.
- Frontend can deploy independently of ETL candidate failure.
- Production data source remains last validated `data.ai.json` when gate is not `PASS`.
- Full frontend + ETL test matrix passes.
