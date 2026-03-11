# ETL Operations Runbook

## Quick Reference

**Published artifact**: `src/data/data.ai.json`  
**Internal artifacts**: `artifacts/market-snapshot.json`, `artifacts/lane-packs.json`, `artifacts/editorial-decisions.json`, `artifacts/editorial-harmonized.json`  
**Entry point**: `scripts/main.py`

## Architecture

The production flow is now:

1. `collect` a broad market snapshot from the curated seed catalog plus best-effort live signals
2. `canonicalize` raw records into market entities
3. `score` explicit adoption, momentum, maturity, breadth, stability, and risk signals
4. `pack` entities into editorial lanes
5. `decide` each lane independently
6. `harmonize` cross-lane duplicates
7. `publish` the stable frontend contract to `src/data/data.ai.json`

The old repo-centric `RadarPipeline` and its shadow-eval path are removed.

## Manual Execution

### Full pipeline run

```bash
PYTHONPATH=scripts .venv/bin/python scripts/main.py
```

### Limit published output

```bash
PYTHONPATH=scripts .venv/bin/python scripts/main.py --max-technologies 12
```

### Restrict discovery sources

```bash
PYTHONPATH=scripts .venv/bin/python scripts/main.py --sources seed_catalog,github_trending,hackernews
```

### Dry run with public preview only

```bash
PYTHONPATH=scripts .venv/bin/python scripts/main.py --dry-run
```

## Output Expectations

- `src/data/data.ai.json` is the only public artifact consumed by the frontend.
- `artifacts/market-snapshot.json` is the debug-friendly internal market dataset.
- `artifacts/lane-packs.json` shows the exact lane payloads prepared for editorial decisions.
- `artifacts/editorial-decisions.json` records per-lane include/exclude outcomes.
- `artifacts/editorial-harmonized.json` shows the final merged decision before publication.

## LLM Behavior

- Lane decisions support an OpenAI-compatible call when `OPENAI_API_KEY` is available.
- If no API key is present or the response is invalid, the pipeline falls back to a deterministic editorial heuristic.
- This keeps the pipeline runnable in CI and local development without blocking publication.

## Troubleshooting

### Issue: noisy GitHub repos appear in the radar

**Cause**: a live GitHub record bypassed canonical seed matching.

**Check**:

```bash
cat artifacts/editorial-harmonized.json
cat artifacts/market-snapshot.json
```

**Fix**:

- tighten seed matching in `scripts/etl/discovery/collector.py`
- add/update a regression test in `scripts/tests/test_discovery_collector.py`

### Issue: run is too slow

**Cause**: live source scans are taking too long.

**Fix**:

- run with `--sources seed_catalog`
- or reduce source fetch scope in the discovery source adapters

### Issue: `data.ai.json` changed shape

**Fix**:

```bash
PYTHONPATH=scripts .venv/bin/pytest -s scripts/tests/test_radar_contract_v2.py
```

### Issue: editorial output looks thin or duplicated

**Fix**:

- inspect `artifacts/lane-packs.json` for candidate depth
- inspect `artifacts/editorial-decisions.json` for lane-level cut decisions
- inspect `artifacts/editorial-harmonized.json` for cross-lane duplicate handling

## Verification Commands

```bash
PYTHONPATH=scripts .venv/bin/pytest -s scripts/tests
npm test
npm run build
```
