# Qualtio Tech Radar - ETL Architecture

## Overview

The Qualtio Tech Radar ETL pipeline automatically identifies, classifies, and tracks technology trends from multiple sources (GitHub, Hacker News) using AI-powered classification.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                           │
├──────────────┬──────────────┬───────────────────────────────┤
│ GitHub API   │ Hacker News  │ Google Trends (future)        │
└──────┬───────┴──────┬───────┴───────────────────────────────┘
       │              │
       ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAW COLLECTION                           │
│  • Leader repositories (>1000 stars)                        │
│  • Trending topics                                        │
│  • HN discussions (>10 points)                            │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    ETL PIPELINE                             │
├─────────────────────────────────────────────────────────────┤
│ 1. EXTRACT                                                │
│    ├─ GitHub API pagination                               │
│    ├─ HN API scraping                                     │
│    └─ Deduplication & normalization                       │
│                                                           │
│ 2. TRANSFORM                                              │
│    ├─ AI Classification (MiniMax-M2.5)                  │
│    ├─ Quadrant assignment                               │
│    ├─ Ring calculation (momentum scores)                │
│    └─ Metadata enrichment                                 │
│                                                           │
│ 3. LOAD                                                   │
│    ├─ Data validation                                     │
│    ├─ Shadow evaluation (quality gate)                    │
│    └─ JSON output (data.ai.json)                        │
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

**GitHub Collection**
- Queries repositories with >1000 stars
- Collects: name, description, stars, topics, language
- Pagination handling for rate limits

**Hacker News Collection**
- Scans stories with >10 points
- Extracts mentions of technologies
- Correlates with GitHub data

### Stage 2: AI Classification (Transform)

**Classification Service**
```python
# Synthetic API Configuration
Model: MiniMaxAI/MiniMax-M2.5
API: https://api.synthetic.new/v1
Fallback: Rule-based heuristics
```

**Classification Logic**
- Input: Technology name + description + GitHub metadata
- Output: Quadrant (platforms|techniques|tools|languages)
- Confidence score: 0.0 - 1.0

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

#### Leader stability policy (strict + temporal inertia)

- Leader threshold remains strict (`leader_coverage > 95%`).
- Leader-set changes use **3-run consecutive confirmation** before promotion.
- Shadow state tracks:
  - `stable_leaders`
  - `candidate_changes` (added/removed + consecutive count)
  - promotion events

This avoids one-run noise while allowing sustained real changes.

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
  "updatedAt": "ISO8601"
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

1. **Google Trends Integration** - Add search volume data
2. **Twitter/X Mentions** - Social sentiment
3. **Reddit Discussions** - Community interest
4. **Stack Overflow** - Developer questions
5. **NPM/DockerHub** - Package metrics

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
