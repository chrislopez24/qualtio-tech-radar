# ETL Operations Runbook

## Quick Reference

**Production URL**: https://chrislopez24.github.io/qualtio-tech-radar/  
**GitHub Repo**: https://github.com/chrislopez24/qualtio-tech-radar  
**Workflow**: Quarterly Tech Radar Update

## Manual Execution

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
- Use 3-run inertia for leader transitions
- Do not promote candidate leader changes until sustained

**Operational behavior**:
1. Read `gate_status` in `artifacts/shadow_eval.json` (`pass|warn|fail`)
2. If `warn`, keep monitoring next runs (candidate changes in report)
3. If `fail`, investigate data quality before approving ETL update
4. Validated `src/data/data.ai.json` remains production source unless gate is `pass`

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
