# ETL Architecture

System architecture for the Tech Radar data pipeline.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     RadarPipeline                                │
├─────────────────────────────────────────────────────────────────┤
│  Sources ─► Normalize ─► Market Score ─► Ring Engine ─► AI/Filter ─► Output │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Sources (`scripts/etl/sources/`)

| Source | Description | API/Scraper |
|--------|-------------|-------------|
| GitHub Trending | Daily trending repositories | GitHub REST API |
| Hacker News | Top stories from past 7 days | Official HN API |
| Google Trends | Interest data for seed topics | Google Trends API |

Each source implements a standard interface:
- `fetch()` - Retrieve raw data
- `normalize()` - Convert to `TechnologySignal` format

### 2. Normalizer (`scripts/etl/normalizer.py`)

Standardizes data from all sources into unified `TechnologySignal` format:
- `name`: Technology name
- `description`: Raw description text
- `source`: Origin (github, hn, trends)
- `url`: Reference URL
- `metadata`: Source-specific data (stars, points, etc.)

### 3. Classifier (`scripts/etl/classifier.py`)

AI-powered classification using Synthetic API:
- **Quadrant**: Platform, Language, Tool, Technique
- **Ring**: Adopt, Trial, Assess, Hold
- **Confidence**: 0.0-1.0 score
- **Rationale**: Short explanation

Classification prompt includes:
- Technology name and description
- Quadrant/ring definitions
- Examples for few-shot learning

### 4. Market Scoring + Ring Engine (`scripts/etl/market_scoring.py`, `scripts/etl/ring_assignment.py`)

Deterministic ring assignment based on external momentum:
- Weighted external signals: GitHub momentum/popularity, Hacker News heat, Google momentum
- Threshold-based initial ring assignment
- Hysteresis on promote/demote transitions
- Distribution guardrail (`max_ring_ratio`) to prevent ring collapse (for example, all-`adopt`)

### 5. History Store (`scripts/etl/history_store.py`)

JSON rolling store for temporal trend/movement:
- Persists `src/data/data.ai.history.json`
- Keeps last `max_weeks` snapshots
- Enables `trend` and `moved` relative to previous snapshot

### 6. Filter (`scripts/etl/pipeline.py`)

Quality gates applied post-classification:
- Minimum confidence threshold (default: 0.5)
- Auto-ignore list (configurable)
- Include-only list (optional override)

### 7. Output Generator (`scripts/etl/output_generator.py`)

Generates radar data files:
- `src/data/data.ai.json` - Public, sanitized
- `src/data/data.ai.history.json` - Rolling temporal history

Sanitization removes:
- Internal URLs
- Sensitive metadata
- Raw API responses

## Resilience Patterns

### Checkpoint (`scripts/etl/checkpoint.py`)

Saves pipeline state after each phase:
- Current phase name
- Cursor position
- Completed phases list

On resume, pipeline continues from last checkpoint.

### Rate Limiter (`scripts/etl/rate_limiter.py`)

Token bucket algorithm:
- Configurable requests per minute
- Per-source token buckets
- Automatic throttling

### Circuit Breaker (`scripts/etl/rate_limiter.py`)

Failure detection for external APIs:
- Tracks failure counts
- Opens circuit after threshold
- Half-open state for recovery
- Auto-reset after timeout

## Data Flow

```
1. Load Config (config.yaml)
2. For each enabled source:
   a. Fetch raw data
   b. Normalize to TechnologySignal
3. Deduplicate by name
4. Compute deterministic market score from external signals
5. Assign rings with hysteresis + guardrails
6. Classify quadrants/descriptions and apply strategic filtering
7. Generate output files (public + rolling history)
8. Save checkpoint
```

## Configuration

`scripts/config.yaml` controls all pipeline behavior:

```yaml
sources:
  github_trending:
    enabled: true
    language: all
    time_range: daily

classification:
  model: hf:MiniMaxAI/MiniMax-M2.5
  temperature: 0.2
  timeout: 30
  max_retries: 3

filtering:
  min_confidence: 0.5
  auto_ignore: []
  include_only: []

rate_limit:
  requests_per_minute: 30

checkpoint:
  enabled: true
  interval: 100
```

## File Structure

```
scripts/
├── etl/
│   ├── __init__.py       # Package entry
│   ├── config.py         # Config loading
│   ├── models.py         # Data models
│   ├── pipeline.py       # Main pipeline
│   ├── normalizer.py     # Data normalization
│   ├── classifier.py     # AI classification
│   ├── output_generator.py
│   ├── checkpoint.py     # State persistence
│   ├── rate_limiter.py   # Rate limiting + circuit breaker
│   ├── temporal_analyzer.py
│   └── sources/          # Source implementations
├── main.py              # CLI entry point
└── config.yaml          # Configuration
```
