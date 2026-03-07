# ETL Operations Runbook

## Quick Reference

**Production URL**: https://chrislopez24.github.io/qualtio-tech-radar/  
**GitHub Repo**: https://github.com/chrislopez24/qualtio-tech-radar  
**Workflow**: Quarterly Tech Radar Update

## Manual Execution

The production ETL run is driven by GitHub, Hacker News, deps.dev, PyPI Stats, and OSV. There is no separate repository deep-scan step to configure or troubleshoot.

### Trigger Pipeline

```bash
# Via GitHub CLI
gh workflow run "Quarterly Tech Radar Update" --repo chrislopez24/qualtio-tech-radar

# Via Web UI
# GitHub → Actions → Quarterly Tech Radar Update → Run workflow
```

### Monitor Progress

```bash
# Watch latest run
gh run watch --repo chrislopez24/qualtio-tech-radar

# View logs
gh run view --repo chrislopez24/qualtio-tech-radar --log

# Web UI
gh run view --repo chrislopez24/qualtio-tech-radar --web
```

## Common Operations

### 1. Check Pipeline Status

```bash
gh run list --repo chrislopez24/qualtio-tech-radar --limit 5
```

### 2. View Shadow Evaluation Results

```bash
# Download artifacts
ghe run download --repo chrislopez24/qualtio-tech-radar --name shadow-eval-report

# View report
cat artifacts/shadow_eval.json
```

### 3. Update Secrets

```bash
# GitHub Token
ghe secret set GH_TOKEN --repo chrislopez24/qualtio-tech-radar
# Paste: ghp_xxx

# AI API Key
ghe secret set SYNTHETIC_API_KEY --repo chrislopez24/qualtio-tech-radar
# Paste: syn_xxx
```

### 4. Emergency Rollback

If deployment fails:

```bash
# Revert to previous data commit
git log --oneline --all -- src/data/
git revert <COMMIT_SHA>
git push
```

## Troubleshooting

### Issue: "AI classifier not available, using fallback"

**Cause**: SYNTHETIC_API_KEY not set or invalid

**Solution**:
```bash
# Verify secret exists
ghe secret list --repo chrislopez24/qualtio-tech-radar

# Update if needed
ghe secret set SYNTHETIC_API_KEY --repo chrislopez24/qualtio-tech-radar
```

### Issue: "Core overlap below threshold"

**Cause**: Significant data degradation or API failures

**Solution**:
1. Check artifacts/shadow_eval.json
2. Review baseline vs current comparison
3. If transient: Re-run pipeline
4. If persistent: Investigate data source issues

### Issue: "Leader coverage failed in one run"

**Cause**: Potential volatility in leader set for current candidate run

**Policy**:
- Keep strict threshold (`leader_coverage >= 0.95`)
- Use 3-run inertia for leader transitions (candidate must persist for 3 consecutive runs)
- Do not promote candidate leader changes until sustained

**Operational behavior**:
1. Read `status` in `artifacts/shadow_eval.json` (`pass|warn|fail`)
2. Check `candidate_changes` for leader IDs with their `consecutive_count` and `change_type`
3. Review `next_action_message` for human-readable guidance on handling the situation
4. If `warn`, keep monitoring next runs (candidate changes in report)
5. If `fail`, investigate data quality before approving ETL update
6. Validated `src/data/data.ai.json` remains production source unless gate is `pass`

**3-Run Inertia Rule**: A candidate leader change must appear in 3 consecutive pipeline runs before promotion. The `consecutive_count` field tracks this progress. Changes with count < 3 remain in candidate state and are not promoted to production.

### Issue: GitHub Pages shows 404

**Cause**: Pages not enabled or basePath misconfiguration

**Solution**:
```bash
# Enable Pages
ghe repo edit chrislopez24/qualtio-tech-radar --enable-pages

# Settings → Pages → Source: GitHub Actions
```

### Issue: Styles not loading (white background)

**Cause**: Missing basePath for GitHub Pages

**Solution**:
Check next.config.ts has basePath set for production builds.

### Issue: "Rate limit exceeded"

**Cause**: GitHub API quota exhausted

**Solution**:
1. Check rate limit: `curl -H "Authorization: token $GH_TOKEN" https://api.github.com/rate_limit`
2. Wait for reset (usually 1 hour)
3. Consider using GitHub App instead of PAT

## LLM Optimization Configuration

The pipeline supports selective LLM classification to reduce API costs while maintaining quality.

### Configuration Options

```yaml
llm_optimization:
  enabled: true                    # Enable selective LLM
  max_calls_per_run: 50           # Budget limit per pipeline run
  borderline_band: 5.0            # Score proximity threshold for borderline
  watchlist_ratio: 0.3            # Ratio of watchlist to core items
  cache_enabled: true             # Enable classification caching
  cache_drift_threshold: 3.0      # Cache drift detection threshold
```

### Selective LLM Policy

Only **borderline** candidates (uncertain classifications near thresholds) are sent to the LLM:

- **Core candidates**: High confidence, classified deterministically
- **Watchlist candidates**: Trending items, classified with heuristics  
- **Borderline candidates**: Uncertain scores, classified via LLM

This achieves ~70% reduction in LLM calls while maintaining quality.

### Shadow Baseline Parameter

For quality validation, provide a shadow baseline for comparison:

```bash
python scripts/main.py --shadow-baseline data.ai.json
```

Metrics compared against baseline:
- `core_overlap`: % of core technologies preserved (>85% threshold)
- `leader_coverage`: % of leaders included (>95% threshold)
- `watchlist_recall`: % of watchlist tracked (>80% threshold)

Notes:
- Use a baseline generated by the same data contract/version when possible.
- Watchlist recall ignores explicit watchlist entries flagged with `missingEvidence` to avoid penalizing valid editorial cleanup.

## V2 Source Controls

The ETL now supports public evidence sources directly from `scripts/config.yaml` or `--sources`:

```bash
python scripts/main.py --sources github_trending,hackernews,deps_dev,pypistats,osv
```

Default production config keeps five enabled (`stackexchange` disabled).

Operational notes:
- `deps.dev`: best effort package dependents
- `pypistats`: Python-only adoption evidence; best-effort, daily-updated, can return `429`
- `osv`: vulnerability pressure
- `deps.dev` and `pypistats` use explicit canonical package mappings to avoid repo-name false positives

If one of these degrades, the run should still complete and the failure is visible under `meta.pipeline.runMetrics.sources`.

Production guidance:
- `SYNTHETIC_API_KEY` is required.
- `GH_TOKEN` is recommended for GitHub quota headroom.
- `deps.dev`, `pypistats`, and `osv` do not require API keys.

### Cache Configuration

Control caching behavior via `cache_enabled` and `cache_drift_threshold`:

- **cache_enabled**: Enable/disable classification caching
- **cache_drift**: Maximum allowed drift before cache invalidation

## Shadow Gate Outcomes and Deploy Behavior

- **PASS**
  - ETL candidate data is eligible for commit
  - deploy proceeds with new validated data
- **WARN**
  - leader drift detected but not yet stable (<3 runs)
  - ETL candidate data is not promoted
  - frontend can still build/deploy using last validated `data.ai.json`
- **FAIL**
  - threshold breach or regression
  - ETL candidate data is not promoted
  - frontend can still build/deploy using last validated `data.ai.json`

The review summary is also an operational gate now:
- it fails when `adopt` contains GitHub-only items
- it fails when `trial` exceeds the GitHub-only ceiling
- it warns when quadrants still lack enough source coverage

## Explainability and Run Metrics

`meta.pipeline` now includes:
- `runMetrics.sources.<source>` with `records`, `durationSeconds`, and `failures`
- `ringQuality`
- `quadrantQuality`
- `quadrantRingQuality`

Each blip may expose:
- `sourceCoverage`
- `sourceFreshness`
- `evidenceSummary`
- `whyThisRing`

Use these before trusting a run. If `trial` or a full quadrant is still GitHub-heavy, do not treat the artifact as publishable just because the ETL succeeded.

## Leader Explainability Fields

The `shadow_eval.json` report includes detailed explainability fields for operational transparency:

### Transition Summary

```json
{
  "leader_transition_summary": {
    "candidate_count": 3,
    "promoted_count": 1
  }
}
```

- `candidate_count`: Number of leaders under evaluation (not yet stable)
- `promoted_count`: Number of leaders that completed the 3-run inertia requirement and were promoted

### Candidate Changes Structure

```json
{
  "candidate_changes": [
    {
      "leader_id": "react",
      "change_type": "demotion",
      "consecutive_count": 2
    }
  ]
}
```

- `leader_id`: Technology identifier for the affected leader
- `change_type`: `promotion` or `demotion` indicating the direction of change
- `consecutive_count`: Number of consecutive runs this change has been observed (1-3, where 3 triggers promotion)

### Action Fields

Two fields guide operational response:

- `next_action`: Machine-readable code for automation (`monitor`, `promote_candidate`, `investigate`)
- `next_action_message`: Human-readable guidance providing context and recommended steps

The `next_action` code remains stable for automation compatibility, while `next_action_message` provides detailed context that may evolve as the system improves.

## What-Changed Panel Data

The Shadow Gate exposes structured data through `meta.shadowGate` in the radar output:

### Status and Metrics

```json
{
  "meta": {
    "shadowGate": {
      "status": "pass",
      "coreOverlap": 0.92,
      "leaderCoverage": 0.96,
      "watchlistRecall": 0.88,
      "filteredCount": 5,
      "addedCount": 3
    }
  }
}
```

- `status`: Gate outcome - `pass`, `warn`, `fail`, or `skip`
- `coreOverlap`: Percentage of core technologies preserved from baseline (0.0-1.0)
- `leaderCoverage`: Percentage of quadrant leaders included in current data (0.0-1.0)
- `watchlistRecall`: Percentage of watchlist items tracked (0.0-1.0)
- `filteredCount`: Number of items filtered by the gate
- `addedCount`: Number of new items added
- `leaderTransitionSummary`: Compact pending/promoted leader counts

### Pipeline Explainability

`meta.pipeline` now exposes compact operator-facing context for each run:

- `rejectedByStage`: Counts for `insufficientSources`, `qualityGate`, and `aiFilter`
- `ringDistribution`: Current radar distribution by ring
- `topAdded`: Small sample of highest-scoring additions vs previous snapshot
- `topDropped`: Small sample of highest-scoring drops vs previous snapshot

These fields are intentionally compact and are designed for dashboards, job summaries, and quick human review rather than full forensic debugging.

### Filtered Sample

When items are filtered, up to 10 example IDs are included:

```json
{
  "filteredSample": ["tech1", "tech2", "tech3"]
}
```

This helps operators understand what types of items are being excluded.

### Candidate Changes and Leader State

The panel includes leader stability tracking:

```json
{
  "candidateChanges": [
    {
      "leaderId": "react",
      "consecutiveCount": 2,
      "changeType": "demotion"
    }
  ],
  "leaderState": {
    "stableLeaders": ["react", "vue", "angular"],
    "candidateChanges": [...],
    "promotedChanges": [...]
  }
}
```

- `candidateChanges`: Leaders under evaluation with their consecutive observation counts
- `leaderState`: Persisted state including stable leaders and change history

## Provenance and Freshness Fields

`AITechnology` supports optional provenance fields for traceability:

```json
{
  "sourceSummary": "GitHub trending + HN mentions",
  "signalFreshness": "2025-03-05T10:30:00Z"
}
```

- `sourceSummary`: High-level origin summary describing data sources (e.g., "GitHub trending + HN mentions", "Industry report Q1 2025")
- `signalFreshness`: ISO8601 timestamp indicating when signals were collected

These fields are optional and only displayed when present to maintain backward compatibility. When absent, the UI displays without provenance information.

## Workflow Caching

The CI pipeline includes caching for improved performance:

### Python Dependencies

- Cache location: `~/.cache/pip`
- Cache key: Hash of `scripts/requirements.txt`
- Effect: Faster workflow execution on subsequent runs when requirements unchanged

### Node.js Dependencies

- Cache key: Hash of `package-lock.json`
- Effect: Preserves `node_modules` between runs

### Cache Invalidation

Changes to `scripts/requirements.txt` or `package-lock.json` trigger fresh dependency installation. This ensures updates are applied while maintaining fast execution for stable dependency sets.

## Configuration Changes

### Update Pipeline Schedule

Edit `.github/workflows/quarterly-update.yml`:

```yaml
on:
  schedule:
    - cron: '0 9 1-7 1,4,7,10 1'  # Quarterly
```

### Modify Thresholds

Edit workflow file, shadow eval step:

```bash
--shadow-threshold-core-overlap 0.85
--shadow-threshold-leader-coverage 0.95
--shadow-threshold-watchlist-recall 0.80
```

### Add New Data Source

1. Create collector in `scripts/collectors/`
2. Update `scripts/main.py`
3. Add tests
4. Update documentation

## Maintenance

### Quarterly Tasks

- [ ] Review classification accuracy
- [ ] Update AI model if needed
- [ ] Check for deprecated technologies
- [ ] Verify all secrets are valid
- [ ] Review performance metrics

### Annual Tasks

- [ ] Rotate API keys
- [ ] Update dependencies
- [ ] Review and update thresholds
- [ ] Archive old data
- [ ] Security audit

## Contacts

**Maintainer**: @chrislopez24  
**Issues**: https://github.com/chrislopez24/qualtio-tech-radar/issues  
**Documentation**: `/docs/etl-architecture.md`

## Appendix

### Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| E001 | AI API timeout | Retry manually |
| E002 | GitHub rate limit | Wait 1 hour |
| E003 | Shadow eval failed | Review artifacts |
| E004 | Data validation failed | Check schema |
| E005 | Pages deploy failed | Verify Pages enabled |

### Environment Setup

```bash
# Local development
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

# Run ETL locally
python scripts/main.py

# Frontend
npm install
npm run dev
```

### Backup & Recovery

**Backup**:
```bash
git clone --mirror https://github.com/chrislopez24/qualtio-tech-radar.git backup.git
```

**Recovery**:
```bash
# Restore from mirror
git clone backup.git
# Or restore specific file
git show <COMMIT>:src/data/data.ai.json > data.ai.json
```
