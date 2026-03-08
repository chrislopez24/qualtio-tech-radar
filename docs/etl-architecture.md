# Qualtio Tech Radar - ETL Architecture

## Overview

The Qualtio Tech Radar ETL pipeline automatically identifies, classifies, and tracks technology trends from external signals and evidence sources (GitHub, Hacker News, deps.dev, PyPI Stats, OSV) using AI-powered classification. Stack Exchange is optional and disabled by default. There is no secondary repository deep-scan phase.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                           │
├──────────────┬──────────────┤
│ GitHub API   │ Hacker News  │ deps.dev       │
│ PyPI Stats   │ OSV          │                │
└──────┬───────┴──────┬────────┴───────┬────────┴──────────┘
       │              │                │
       ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAW COLLECTION                           │
│  • Leader repositories and GitHub momentum                  │
│  • HN discussions and Stack Exchange tag activity           │
│  • Package adoption, dependents, and vulnerability pressure │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    ETL PIPELINE                             │
├─────────────────────────────────────────────────────────────┤
│ 1. EXTRACT                                                │
│    ├─ Source registry bootstraps enabled providers        │
│    ├─ Evidence adapters normalize external records        │
│    └─ Deduplication & normalization                       │
│                                                           │
│ 2. TRANSFORM                                              │
│    ├─ AI Classification (MiniMax-M2.5)                  │
│    ├─ Canonical entity + evidence enrichment            │
│    ├─ Evidence scoring (`adoption`, `mindshare`,        │
│    │  `health`, `risk`)                                 │
│    ├─ Ring policy gates + editorial ceilings            │
│    └─ Explainability + quality metadata                  │
│                                                           │
│ 3. LOAD                                                   │
│    ├─ Artifact quality summaries                          │
│    ├─ Shadow evaluation (quality gate)                    │
│    └─ JSON output (data.ai.json)                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   DATA STORAGE                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  data.ai.json          Current snapshot             │  │
│  │  data.ai.history.json  Historical data               │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Pipeline Stages

### Stage 1: Data Collection (Extract)

**Source Registry**
- The pipeline builds all enabled providers through `etl/source_registry.py`
- Runtime metrics for each provider are captured in `etl/run_metrics.py`

**Evidence Adapters**
- `github_trending`: repo momentum and popularity
- `hackernews`: discussion heat
- `stackexchange`: optional tag activity / mindshare (disabled by default)
- `deps.dev`: reverse dependents and package linkage
- `pypistats`: monthly download pressure for Python packages
- `osv`: known vulnerability pressure

### Stage 2: AI Classification (Transform)

**Classification Service**
```python
# Synthetic API Configuration
Model: MiniMaxAI/MiniMax-M2.5
API: https://api.synthetic.new/v1
Fallback: Rule-based heuristics
```

**Classification Logic**
- Input: Technology name + description + source signals + evidence context
- Output: Quadrant (platforms|techniques|tools|languages)
- Confidence score: 0.0 - 1.0

### Evidence-Based Scoring

The v2 scorer uses four sub-scores:

| Score | Purpose |
|------|---------|
| `adoption` | Package downloads, reverse dependents, and GitHub adoption proxies |
| `mindshare` | Hacker News heat plus Stack Exchange tag activity |
| `health` | Maintenance strength and corroboration breadth |
| `risk` | Vulnerability pressure from OSV |

The ring policy then applies explicit gates:
- `adopt` requires corroborated non-GitHub adoption
- `trial` requires corroboration or an editorial exception
- `assess` and `hold` remain available for promising but weakly corroborated items
- mono-source GitHub candidates are allowed into `assess` only when editorially plausible and clearly above the soft admission floor (otherwise they stay out)

### Selective LLM Optimization

To reduce API costs while maintaining quality, the pipeline implements a **selective LLM policy**:

#### Candidate Categories

Technologies are categorized into three groups based on signal confidence:

| Category | Criteria | LLM Usage | Typical % |
|----------|----------|-----------|-----------|
| **Core** | High confidence (>70%), strong market signals | Deterministic rules | ~50% |
| **Watchlist** | Trending items, moderate signals | Heuristic classification | ~30% |
| **Borderline** | Uncertain scores, near thresholds | LLM classification | ~20% |

#### Borderline Candidates

**Borderline** technologies are identified when:
- Market score within `borderline_band` (default: 5 points) of core threshold
- Confidence score near threshold (70%)
- Trend delta near watchlist threshold

Only borderline candidates are sent to the LLM, achieving ~70% reduction in API calls.

#### Shadow Evaluation

Quality metrics validate selective LLM effectiveness:

| Metric | Description | Threshold |
|--------|-------------|-----------|
| `core_overlap` | % of core technologies preserved vs baseline | >85% |
| `leader_coverage` | % of GitHub leaders included | >95% |
| `watchlist_recall` | % of watchlist items tracked | >80% |

### Stage 3: Quality Gate (Shadow Evaluation)

Before promoting ETL candidate data, the pipeline validates:

| Metric | Threshold | Purpose |
|--------|-----------|---------|
| Core Overlap | >85% | Ensure stable technologies persist |
| Leader Coverage | >95% | Verify data completeness for leaders |
| Watchlist Recall | >80% | Maintain tracking continuity |
| LLM Reduction | >0% | Track efficiency improvements |

#### Leader Stability Policy

The leader stability policy prevents one-run noise while allowing sustained real changes:

**3-Run Consecutive Confirmation**
- Leader threshold remains strict (`leader_coverage > 95%`)
- Changes to the leader-set require **3 consecutive runs** of the same change before promotion
- This creates temporal inertia that filters out transient data fluctuations

**Candidate Tracking**
The shadow evaluation maintains state for:
- `stable_leaders`: Current confirmed leaders
- `candidate_changes`: Pending changes with metadata:
  - `leaderId`: Identifier of the leader
  - `changeType`: "added" or "removed"
  - `consecutive_count`: Number of consecutive runs showing this change (1-3)
- `promoted_changes`: Changes that reached 3 runs and were promoted

**Promotion Events**
When a candidate reaches 3 consecutive runs:
1. It is removed from `candidate_changes`
2. It is added to `promoted_changes`
3. The actual leader set is updated
4. Deterministic serialization ensures consistent persistence across runs

#### Explainability and Observability

The `shadow_eval.json` file includes structured explainability fields for auditing and debugging:

**`leader_transition_summary`**
```json
{
  "candidateChanges": 5,
  "promotedChanges": 2
}
```
- `candidateChanges`: Number of pending changes in the candidate pool
- `promotedChanges`: Number of changes promoted to stable this run

**`candidate_changes` (per-candidate details)**
```json
{
  "candidate_changes": [
    {
      "leaderId": "react",
      "changeType": "added",
      "consecutive_count": 2
    }
  ]
}
```

**Action Fields (Next Action Contract)**
The shadow evaluation provides machine-readable action guidance:

| Field | Purpose | Stability |
|-------|---------|-----------|
| `next_action` | Machine-readable action code (e.g., `promote_candidate`, `wait_for_confirmation`) | Stable for automation |
| `next_action_message` | Human-readable explanation | May change |
| `next_action_code` | Stable integer code for programmatic handling | Stable for automation |

The `next_action` field is specifically designed to be **machine-readable and stable** for automation systems.

#### What-Changed Metadata Contract

The `meta.shadowGate` field in the ETL output provides a stable contract for downstream consumers:

```json
{
  "meta": {
    "shadowGate": {
      "status": "WARN",
      "coreOverlap": 92.5,
      "leaderCoverage": 97.8,
      "watchlistRecall": 85.2,
      "llmCallReduction": 72.1,
      "filteredCount": 8,
      "addedCount": 2,
      "filteredSample": ["tech-a", "tech-b"],
      "leaderState": {
        "stableLeaders": [...],
        "candidateChanges": [...],
        "promotedChanges": [...]
      }
    }
  }
}
```

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `PASS`, `WARN`, or `FAIL` |
| `coreOverlap` | number | % of core technologies preserved vs baseline |
| `leaderCoverage` | number | % of GitHub leaders included |
| `watchlistRecall` | number | % of watchlist items tracked |
| `llmCallReduction` | number | % reduction in LLM calls vs full classification |
| `filteredCount` | number | Technologies filtered this run |
| `addedCount` | number | Technologies added this run |
| `filteredSample` | array | Sample of filtered technology IDs (up to 5) |
| `leaderState.stableLeaders` | array | Current confirmed leader IDs |
| `leaderState.candidateChanges` | array | Pending changes with `leaderId`, `changeType`, `consecutiveCount` |
| `leaderState.promotedChanges` | array | Changes promoted this run |

#### Provenance Tracking

Technology objects may include optional provenance fields for data lineage:

| Field | Type | Description |
|-------|------|-------------|
| `sourceSummary` | string | Summary of data origin (e.g., "GitHub API + HN mentions") |
| `signalFreshness` | string (ISO8601) | Timestamp when signals were collected |
| `sourceCoverage` | number | Number of corroborating source families |
| `sourceFreshness` | object | Freshest/stalest evidence age in days |
| `evidenceSummary` | object | Compact evidence sources and metric families |
| `whyThisRing` | string | Human-readable ring explanation |

## Internal Refactor Boundaries

The ETL coordinator now keeps source semantics and quality summaries out of the orchestration body:

- `etl/source_registry.py`: source construction
- `etl/run_metrics.py`: per-source records, timings, failures
- `etl/artifact_quality.py`: ring/quadrant/quadrant×ring quality summaries
- `etl/pipeline.py`: orchestration only

Both fields are **optional** to maintain backward compatibility with existing data.

#### Gate statuses

- `PASS`: thresholds met, no blocking instability
- `WARN`: thresholds met but leader changes are still candidate (<3 runs)
- `FAIL`: threshold breach or quality regression

Shadow report (`artifacts/shadow_eval.json`) includes gate status and transition summary for auditability.

### Stage 4: Deployment

Workflow behavior is decoupled:

1. ETL candidate run + shadow eval always execute.
2. Candidate data is committed only when shadow gate is `PASS`.
3. If gate is `WARN`/`FAIL`, workflow restores validated baseline data.
4. Frontend build/deploy can continue using validated repository data (`src/data/data.ai.json`).

## Configuration

### Environment Variables

```bash
# GitHub
GH_TOKEN=ghp_xxx                          # Personal access token

# AI Classification (Synthetic)
SYNTHETIC_API_KEY=syn_xxx                 # API key
SYNTHETIC_API_URL=https://api.synthetic.new/v1
SYNTHETIC_MODEL=hf:MiniMaxAI/MiniMax-M2.5

# Pipeline Filters
MIN_STARS=100                             # Minimum GitHub stars
HN_MIN_POINTS=10                          # Minimum HN points
MAX_TECHNOLOGIES=50                       # Maximum technologies to track
```

## Data Schema

### Technology Object

```json
{
  "id": "string",           // Unique identifier
  "name": "string",         // Display name
  "description": "string",  // Short description
  "quadrant": "string",     // platforms|techniques|tools|languages
  "ring": "string",         // adopt|trial|assess|hold
  "githubStars": number,    // Star count
  "hnMentions": number,     // HN mentions
  "confidence": number,     // AI confidence (0-1)
  "trend": "string",        // up|down|stable|new
  "moved": number,          // Ring movement (+/-)
  "updatedAt": "ISO8601",
  "sourceSummary": "string",     // (Optional) Data origin summary
  "signalFreshness": "ISO8601"   // (Optional) Signal collection timestamp
}
```

### Radar Output

```json
{
  "technologies": [...],     // Array of Technology objects
  "watchlist": [...],        // Emerging technologies
  "meta": {
    "generatedAt": "ISO8601",
    "totalTechnologies": number,
    "aiClassified": number
  }
}
```

## Error Handling

### Fallback Strategy

When AI classification fails:
1. Retry with exponential backoff (3 attempts)
2. Use rule-based classification (keywords)
3. Mark with `confidence: 0` and flag for review

### Data Persistence

All intermediate states saved:
- `artifacts/baseline.json` - Previous run
- `artifacts/shadow_eval.json` - Quality report
- `artifacts/etl.log` - Execution logs

## Performance

### Typical Run Metrics

- **Duration**: 2-3 minutes
- **LLM Calls**: ~50 (depends on new technologies)
- **Data Points**: 40-50 technologies
- **Success Rate**: >95%

### Optimization Strategies

1. **Caching**: Classify only new/changed technologies
2. **Batching**: Group API calls
3. **Parallelization**: GitHub + HN in parallel
4. **Rate Limiting**: Respect API quotas

### CI Performance

The `quarterly-update.yml` workflow implements dependency caching for improved CI performance:

**Python Dependencies**
- pip cache keyed by `requirements.txt`
- Automatically restored on cache hits
- Reduces package installation time

**Node.js Dependencies**
- npm cache keyed by `package-lock.json`
- Cached `node_modules` directory
- Faster build times on subsequent runs

Cache keys are derived from:
- `requirements.txt` hash → Python dependencies
- `package-lock.json` hash → Node.js dependencies

## Monitoring

### Key Metrics

```
etl.pipeline.duration_ms
etl.pipeline.technologies.count
etl.ai.classification.confidence.avg
etl.shadow_eval.core_overlap
github.api.rate_limit.remaining
```

### Alerts

Trigger on:
- Core overlap < 85%
- AI classification unavailable
- GitHub API rate limit < 10%
- Pipeline duration > 10 minutes

## Security

### Secrets Management

All credentials stored in GitHub Secrets:
- `GH_TOKEN` - GitHub API
- `SYNTHETIC_API_KEY` - AI service
- Never commit to repository

### Data Sanitization

- Remove PII from descriptions
- Validate all inputs
- Escape special characters
- Limit description length

## Future Improvements

### Planned Features

1. **Twitter/X Mentions** - Social sentiment
2. **Reddit Discussions** - Community interest
3. **Stack Overflow** - Developer questions
4. **NPM/DockerHub** - Package metrics

### Technical Debt

- [ ] Implement incremental updates
- [ ] Add retry logic for flaky APIs
- [ ] Cache AI classifications locally
- [ ] Parallel AI classification
- [ ] Real-time webhook support

---

**Version**: 1.0.0  
**Last Updated**: 2026-02-26  
**Maintainer**: Qualtio Engineering
