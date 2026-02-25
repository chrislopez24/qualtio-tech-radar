# ETL Operations Runbook

Operational guide for running and maintaining the Tech Radar ETL pipeline.

## Prerequisites

### Required Environment Variables

| Variable | Description | How to Get |
|----------|-------------|------------|
| `GH_TOKEN` | GitHub PAT with `repo` scope | [GitHub Settings](https://github.com/settings/tokens) |
| `SYNTHETIC_API_KEY` | Synthetic API key | Sign up at [synthetic.new](https://synthetic.new) |
| `SYNTHETIC_MODEL` | Model identifier (optional) | Default: `hf:MiniMaxAI/MiniMax-M2.5` |

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r scripts/requirements.txt

# Configure environment
cp .env.example .env.local
# Edit .env.local with your API keys
```

## Running the Pipeline

### Basic Execution

```bash
source .venv/bin/activate
python scripts/main.py
```

### Selective LLM Mode (Optimized)

```bash
# Run with selective LLM (reduces API calls by ~70%)
python scripts/main.py
```

The selective LLM policy is **enabled by default** and classifies:
- **Core candidates** (high market score): Deterministic (no LLM)
- **Watchlist candidates** (trending): Deterministic (no LLM)
- **Borderline candidates** only: LLM classification

### Dry Run (No Data Collection)

```bash
python scripts/main.py --dry-run
```

Useful for verifying:
- Configuration is correct
- API connections work
- No syntax errors

### Selective Sources

```bash
# Run only GitHub and HN
python scripts/main.py --sources github_trending,hackernews

# Single source
python scripts/main.py --sources google_trends
```

### Resume from Checkpoint

```bash
python scripts/main.py --resume
```

Use after:
- Interrupted run
- API failure mid-pipeline
- Testing changes mid-execution

### Shadow Mode (Quality Validation)

Run pipeline in shadow mode to validate optimized output against baseline:

```bash
# Basic shadow mode (uses default thresholds)
python scripts/main.py --shadow --shadow-baseline src/data/baseline.json

# Custom thresholds
python scripts/main.py \
  --shadow \
  --shadow-baseline src/data/baseline.json \
  --shadow-threshold-core-overlap 0.90 \
  --shadow-threshold-leader-coverage 0.98 \
  --shadow-threshold-watchlist-recall 0.85 \
  --shadow-threshold-llm-reduction 0.65 \
  --shadow-output artifacts/shadow_eval.json
```

**Quality Thresholds** (default):
- Core Overlap: ≥85% (Jaccard similarity of technology IDs)
- Leader Coverage: ≥95% (adopt ring technologies preserved)
- Watchlist Recall: ≥80% (trending technologies preserved)
- LLM Reduction: ≥60% (API call reduction achieved)

**Output**: Report written to `artifacts/shadow_eval.json` with detailed metrics.

**Go/No-Go**: Pipeline exits with code 1 if any threshold not met, blocking automatic rollout.

**Generate Baseline**:
```bash
# First, generate baseline with full LLM mode (if needed)
# Then copy to baseline file
cp src/data/data.ai.json src/data/baseline.json
```

### Limit Processing

```bash
# Process max 25 technologies
python scripts/main.py --max-technologies 25
```

Useful for testing or limiting API costs.

## Troubleshooting

### Issue: Import Errors

```bash
# Run from scripts directory
cd scripts
source ../.venv/bin/activate
python -m pytest tests -q
```

### Issue: API Rate Limiting

- Check `GH_TOKEN` is set
- Reduce `requests_per_minute` in config.yaml
- Circuit breaker will auto-skip failing sources

### Issue: Classification Failures

- Verify `SYNTHETIC_API_KEY` is valid
- Check `SYNTHETIC_MODEL` is available
- Increase `timeout` in config.yaml

### Issue: Checkpoint Corruption

```bash
# Delete checkpoint to start fresh
rm -f .checkpoint/radar.json
python scripts/main.py
```

### Issue: Empty Output

1. Verify sources are enabled in config.yaml
2. Check API keys are valid
3. Run with `--dry-run` to see configuration

### Issue: Ring Collapse (for example, almost all `adopt`)

1. Verify `distribution_guardrail.enabled` is `true`
2. Check `distribution_guardrail.max_ring_ratio` in `scripts/config.yaml`
3. Confirm `scoring.weights` are not skewed to one source
4. Inspect `src/data/data.ai.history.json` for temporal drift

## Validation Checklist

Run these checks after any pipeline changes:

### 1. Sources Fetch

```bash
# Dry run shows source configuration
python scripts/main.py --dry-run
```

Verify all enabled sources appear in output.

### 2. Classification Quality

Check output file for:
- All items have `quadrant` and `ring`
- Confidence scores above threshold
- No empty `rationale` fields

```bash
# Inspect output
cat src/data/data.ai.json | python -m json.tool | less
```

### 3. Filtering Quality

- No unwanted technologies in output
- Expected technologies present
- Confidence distribution looks reasonable

### 4. Output Integrity

```bash
# Validate JSON
python -c "import json; json.load(open('src/data/data.ai.json'))"
python -c "import json; json.load(open('src/data/data.ai.history.json'))"
```

## Monitoring

### GitHub Actions (Weekly)

The pipeline runs automatically via `.github/workflows/weekly-update.yml`:
- Triggers every Monday at 9 AM UTC
- Uses secrets: `GH_TOKEN`, `SYNTHETIC_API_KEY`
- Outputs to `src/data/data.ai.json` and `src/data/data.ai.history.json`

### Shadow Mode in CI/CD

Add shadow mode validation to workflows before rollout:

```yaml
- name: Run Shadow Evaluation
  run: |
    source .venv/bin/activate
    python scripts/main.py \
      --shadow \
      --shadow-baseline src/data/baseline.json \
      --shadow-output artifacts/shadow_eval.json
    
- name: Upload Shadow Report
  uses: actions/upload-artifact@v4
  with:
    name: shadow-eval-report
    path: artifacts/shadow_eval.json
```

### Cache Monitoring

Monitor LLM cache performance:

```bash
# Check cache hit rate
ls -lh src/data/llm_cache.json

# Clear cache if needed
rm src/data/llm_cache.json
```

**When to Clear Cache**:
- After major config changes
- When prompt version changes
- If cache corruption suspected
- Quarterly cleanup

### Manual Verification

After automated run:
1. Check workflow run status
2. Verify `data.ai.json` and `data.ai.history.json` were updated
3. Check radar displays new data
4. Review shadow eval report (if shadow mode enabled)

## Configuration Reference

### LLM Optimization Config

```yaml
llm_optimization:
  enabled: true              # Enable selective LLM (default: true)
  max_calls_per_run: 40      # Budget limit per pipeline run
  borderline_band: 5.0       # Score band around thresholds for borderline classification
  watchlist_ratio: 0.25      # % of target_total for watchlist bucket
  cache_enabled: true        # Enable drift-aware LLM cache
  cache_file: "src/data/llm_cache.json"
  cache_drift_threshold: 3.0  # Max signal drift before cache invalidation
```

**Tuning Guide**:
- `max_calls_per_run`: Lower = fewer API calls, may miss some borderline candidates
- `borderline_band`: Higher = more borderline candidates get LLM classification
- `watchlist_ratio`: Higher = more slots for trending technologies
- `cache_drift_threshold`: Lower = more cache hits, but may use stale decisions

### Source Config

```yaml
sources:
  github_trending:
    enabled: true
    language: all        # or specific: python, javascript
    time_range: daily    # daily, weekly, monthly
  hackernews:
    enabled: true
    min_points: 10       # minimum HN points
    days_back: 7         # how far back to fetch
  google_trends:
    enabled: true
    seed_topics:         # topics to search
      - python
      - javascript
```

### Classification Config

```yaml
classification:
  model: hf:MiniMaxAI/MiniMax-M2.5
  temperature: 0.2       # lower = more deterministic
  json_mode: true        # always use JSON
  timeout: 30            # seconds per request
  max_retries: 3         # retry failed requests
```

### Rate Limiting

```yaml
rate_limit:
  requests_per_minute: 30
  max_retries: 3
```

### Checkpoint

```yaml
checkpoint:
  enabled: true
  interval: 100          # save every N items
```

## Emergency Procedures

### Pipeline Stuck

1. Check for checkpoint: `cat .checkpoint/radar.json`
2. Delete checkpoint: `rm -f .checkpoint/radar.json`
3. Re-run: `python scripts/main.py`

### API Key Compromised

1. Revoke key in provider console
2. Update `.env.local` with new key
3. Re-run pipeline

### Data Quality Issues

1. Adjust `min_confidence` in config.yaml
2. Add to `auto_ignore` list
3. Re-run with `--resume` or fresh start

### Issue: Selective LLM Not Reducing Calls

**Symptoms**: API calls still high despite selective LLM enabled

**Diagnosis**:
```bash
# Check how many borderline candidates
# Look for log line: "Phase 4 - Candidate selection: X core, Y watchlist, Z borderline"
```

**Solutions**:
1. Increase `borderline_band` to reduce borderline candidates
2. Increase `max_calls_per_run` if hitting budget
3. Tune `watchlist_ratio` to balance buckets
4. Verify `llm_optimization.enabled: true` in config

### Issue: Cache Not Working

**Symptoms**: Same technologies being classified repeatedly

**Diagnosis**:
```bash
# Check if cache file exists and is readable
cat src/data/llm_cache.json | head -5

# Check logs for "Cache hit" or "Cache miss"
grep -i "cache" scripts/main.py.log 2>/dev/null || echo "Check console output"
```

**Solutions**:
1. Verify `llm_optimization.cache_enabled: true`
2. Check cache file permissions
3. Clear cache: `rm src/data/llm_cache.json`
4. Lower `cache_drift_threshold` for more hits

### Issue: Shadow Mode Fails Quality Gates

**Symptoms**: Pipeline exits with code 1, "Quality thresholds not met"

**Diagnosis**:
```bash
# Review shadow eval report
cat artifacts/shadow_eval.json | python -m json.tool

# Check specific metrics
cat artifacts/shadow_eval.json | jq '.core_overlap, .leader_coverage, .watchlist_recall'
```

**Solutions**:
1. **Core Overlap Low**: Adjust `borderline_band` to include more technologies
2. **Leader Coverage Low**: Lower threshold or increase `max_calls_per_run`
3. **Watchlist Recall Low**: Increase `watchlist_ratio`
4. **LLM Reduction Low**: Verify selective LLM is enabled

**Emergency Override** (use with caution):
```bash
# Temporarily lower thresholds
python scripts/main.py \
  --shadow \
  --shadow-baseline src/data/baseline.json \
  --shadow-threshold-core-overlap 0.70 \
  --shadow-threshold-llm-reduction 0.40
```

## Testing

```bash
# Full test suite
cd scripts
source ../.venv/bin/activate
python -m pytest tests -q

# Expected: 58 passed (1 unrelated failure possible)

# Frontend build
npm run build
```
