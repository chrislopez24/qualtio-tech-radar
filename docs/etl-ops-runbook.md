# ETL Operations Runbook

Operational guide for running and maintaining the Tech Radar ETL pipeline.

## Prerequisites

### Required Environment Variables

| Variable | Description | How to Get |
|----------|-------------|------------|
| `GH_TOKEN` | GitHub PAT with `repo` scope | [GitHub Settings](https://github.com/settings/tokens) |
| `SYNTHETIC_API_KEY` | Synthetic API key | Sign up at [synthetic.new](https://synthetic.new) |
| `SYNTHETIC_MODEL` | Model identifier (optional) | Default: `llama-3.3-70b` |

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
```

## Monitoring

### GitHub Actions (Weekly)

The pipeline runs automatically via `.github/workflows/weekly-update.yml`:
- Triggers every Sunday at 2 AM UTC
- Uses secrets: `GH_TOKEN`, `SYNTHETIC_API_KEY`
- Outputs to `src/data/data.ai.json`

### Manual Verification

After automated run:
1. Check workflow run status
2. Verify `data.ai.json` was updated
3. Check radar displays new data

## Configuration Reference

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
  model: gpt-4           # or other models
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