# ETL Architecture

System architecture for the Tech Radar data pipeline.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     RadarPipeline                                │
├─────────────────────────────────────────────────────────────────┤
│  Sources ──► Normalize ──► Classify ──► Filter ──► Output      │
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

### 4. Filter (`scripts/etl/pipeline.py`)

Quality gates applied post-classification:
- Minimum confidence threshold (default: 0.5)
- Auto-ignore list (configurable)
- Include-only list (optional override)

### 5. Output Generator (`scripts/etl/output_generator.py`)

Generates radar data files:
- `src/data/data.ai.json` - Public, sanitized
- `src/data/data.ai.full.json` - Internal, full metadata

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
4. Classify each signal (batch API calls)
5. Apply filters (confidence, lists)
6. Generate output files
7. Save checkpoint
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
  model: gpt-4
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
├── scraper/              # Legacy scrapers
├── ai/                   # Legacy classifier
├── main.py              # CLI entry point
└── config.yaml          # Configuration
```