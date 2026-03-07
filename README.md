# Qualtio Tech Radar

AI-powered Technology Radar with automated weekly updates from GitHub, Hacker News, Stack Exchange, deps.dev, PyPI Stats, and OSV. Rings are assigned by evidence-based scoring plus editorial gates so strong rings require corroborated adoption instead of raw repo popularity.

![Tech Radar Preview](./docs/preview.png)

## Features

- **Interactive Radar Visualization**: Custom D3.js-based radar with 4 quadrants and 4 rings
- **AI-Only Radar**: AI-powered classification and weekly refresh pipeline
- **Selective LLM Optimization**: 70%+ reduction in LLM calls via intelligent candidate selection (core/watchlist/borderline)
- **Drift-Aware Caching**: Reuse LLM decisions across runs with automatic invalidation
- **Shadow Quality Evaluation**: Validate optimized pipeline against baseline with pass/warn/fail quality gate outcomes
- **Operational Explainability**: Shadow evaluation reports with leader transition visibility and "what changed" insights
- **Evidence-Based Ring Policy**: `adopt` and `trial` now require corroborated evidence instead of GitHub-only momentum
- **Explainable Artifact v2**: Each blip can expose `sourceCoverage`, `sourceFreshness`, `evidenceSummary`, and `whyThisRing`
- **Editorial False-Positive Guardrails**: Resource-like repositories (awesome lists, books, roadmaps, prompt collections) are treated separately from real technologies
- **Professional ETL Boundaries**: Source registry, run metrics, artifact quality summaries, and compact operational metadata
- **Glassmorphism UI**: Modern, responsive design with dark theme support
- **Automated Data Pipeline**: Weekly updates via GitHub Actions
- **Market-Signal Ringing**: External momentum scoring (GitHub + HN) with anti-collapse guardrails
- **Search & Filter**: Real-time search across all technologies

## Tech Stack

- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS + Framer Motion
- **Visualization**: D3.js
- **UI Components**: Local Radix-based component primitives
- **Data Pipeline**: Python 3.12 + Synthetic API
  - Selective LLM classification (70%+ call reduction)
  - Drift-aware decision caching
  - Shadow quality evaluation
  - Evidence source adapters (`deps.dev`, `Stack Exchange`, `PyPI Stats`, `OSV`)
  - Source registry + run metrics
  - Candidate selection (core/watchlist/borderline)

## Local Development

### Prerequisites

- Node.js 20+ 
- Python 3.11+
- Git

### 1. Clone & Install

```bash
git clone https://github.com/chrislopez24/qualtio-tech-radar.git
cd qualtio-tech-radar

# Install Node.js dependencies
npm install

# (Optional) Install Python dependencies for data pipeline
pip install -r scripts/requirements.txt
```

### 2. Environment Setup

Copy the example environment file and configure:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your API keys (only needed if running the data pipeline locally):

```env
SYNTHETIC_API_KEY=your_synthetic_api_key_here
SYNTHETIC_API_URL=https://api.synthetic.new/v1
SYNTHETIC_MODEL=hf:MiniMaxAI/MiniMax-M2.5

# Optional but recommended for source reliability
GH_TOKEN=your_github_token_here
STACKEXCHANGE_KEY=your_stackexchange_key_here
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Build for Production (Local Test)

```bash
npm run build
```

The static site will be generated in the `dist/` folder.

## Project Structure

```
├── src/
│   ├── app/              # Next.js app router
│   ├── components/       # React components (Radar, Blip, etc.)
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # Utilities & configuration
│   └── data/             # AI-generated radar data (JSON)
├── scripts/              # Python data pipeline
│   ├── etl/              # ETL pipeline, sources, scoring, filtering
│   ├── tests/            # Pytest coverage for ETL/workflow contracts
│   └── main.py           # Pipeline entry point
├── .github/workflows/    # CI/CD automation
└── docs/                 # Operational and architectural documentation (A+C hardening details)
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build static export for production |
| `npm run lint` | Run ESLint |
| `npm start` | Start production server (after build) |

## Data Pipeline (ETL)

The ETL pipeline collects external technology signals from GitHub, Hacker News, Stack Exchange, deps.dev, PyPI Stats, and OSV, classifies them using AI, and generates the radar data files. It does not perform a secondary repository deep-scan pass.

### Quick Start

```bash
# Ensure you have .env.local configured with API keys
source .venv/bin/activate
python scripts/main.py
```

This will:
1. Fetch external signals plus evidence records from GitHub, Hacker News, Stack Exchange, deps.dev, PyPI Stats, and OSV
2. Compute evidence-based sub-scores (`adoption`, `mindshare`, `health`, `risk`) per technology
3. Assign rings using policy gates, hysteresis, and editorial guardrails
4. Classify quadrants/descriptions with Synthetic API support
5. Apply editorial filtering to keep resource collections out of strong technology rings
6. Generate `src/data/data.ai.json` and `src/data/data.ai.history.json`

### Environment Variables

Environment used by the pipeline:

| Variable | Description | Required |
|----------|-------------|----------|
| `SYNTHETIC_API_KEY` | API key for Synthetic (LLM) classification | Yes |
| `SYNTHETIC_MODEL` | Model to use (default: `hf:MiniMaxAI/MiniMax-M2.5`) | No |
| `SYNTHETIC_API_URL` | Synthetic API endpoint (default: `https://api.synthetic.new/v1`) | No |
| `GH_TOKEN` | GitHub personal access token for higher GitHub API quota | No |
| `STACKEXCHANGE_KEY` | Stack Exchange API key for mindshare coverage stability | No, but strongly recommended for production |

Use `SYNTHETIC_MODEL` to switch models (for example, `hf:moonshotai/Kimi-K2.5` for evaluation runs). Keep `SYNTHETIC_API_URL` unchanged unless your environment explicitly requires a different endpoint.

Source-specific notes:
- `deps.dev`, `PyPI Stats`, and `OSV` work without API keys.
- `Stack Exchange` is public, but keyless access is fragile on shared IPs and can be throttled for hours. Production runs should set `STACKEXCHANGE_KEY`.
- `PyPI Stats` is best-effort and can return `429` under bursty access. The ETL uses persistent cache plus explicit package mapping to keep it useful without over-querying.
- `deps.dev` evidence is only attached for curated canonical package mappings, not by naive repo-name fallback.

### Source Toggles

Enable/disable data sources in `scripts/config.yaml`:

```yaml
sources:
  github_trending:
    enabled: true
  hackernews:
    enabled: true
  deps_dev:
    enabled: true
  stackexchange:
    enabled: true
  pypistats:
    enabled: true
  osv:
    enabled: true
```

Or via CLI:
```bash
python scripts/main.py --sources github_trending,hackernews,deps_dev,stackexchange,pypistats,osv
```

### Pipeline Options

```bash
# Dry run (simulate without collecting data)
python scripts/main.py --dry-run

# Resume from checkpoint (after interruption)
python scripts/main.py --resume

# Limit radar output size
python scripts/main.py --max-technologies 25
```

### Checkpoint & Resume

The pipeline saves checkpoints automatically (every 100 items by default). If interrupted:
- Use `--resume` to continue from where it left off
- Checkpoint file: `.checkpoint/radar.json`
- Delete checkpoint to start fresh

### Quality Guardrails

The pipeline includes:
- **Confidence threshold**: `min_confidence: 0.5` (config.yaml)
- **Rate limiting**: 30 requests/minute to prevent API throttling
- **Circuit breaker**: Automatically skips failing sources
- **Retry logic**: 3 retries with exponential backoff
- **Ring guardrails**: Hysteresis and max-ring-ratio fallback rebalance to avoid all-`adopt`
- **Publishability checks**: Review summary fails when `adopt` is GitHub-only or `trial` exceeds the GitHub-only ceiling
- **Leader explainability**: Leader transition visibility with `consecutiveCount` tracking (3-run stability confirmation required for leader-set changes)
- **Shadow evaluation gate**: `meta.shadowGate` contract provides operational visibility into quality metrics and "what changed" insights
- **Decoupled deploy behavior**: frontend deploy can continue with last validated `src/data/data.ai.json` when ETL gate is warn/fail

### Shadow Evaluation Metadata

The pipeline outputs a `meta.shadowGate` object in `data.ai.json` for operational visibility:

| Field | Description |
|-------|-------------|
| `status` | Quality gate outcome: `pass`, `warn`, or `fail` |
| `quality.coreOverlap` | % of core technologies retained vs full-run baseline |
| `quality.leaderCoverage` | % of quadrant leaders present (strict threshold) |
| `quality.watchlistRecall` | % of watchlist technologies retained |
| `changes.filteredCount` | Technologies filtered by optimization (LLM call reduction) |
| `changes.addedCount` | New technologies added this run |
| `pipeline.rejectedByStage` | Compact rejection reasons from ETL filtering stages |
| `pipeline.ringDistribution` | Current radar mix by ring (`adopt`/`trial`/`assess`/`hold`) |
| `pipeline.topAdded` | Sample of highest-scoring additions vs previous snapshot |
| `pipeline.topDropped` | Sample of highest-scoring drops vs previous snapshot |
| `candidateChanges` | Leader stability tracking with `consecutiveCount` for each transition |
| `leaderTransitionSummary` | Pending/promoted leader transition counts for quick ops review |

This provides "what changed" visibility for operations teams monitoring pipeline health.

### Explainable Blip Fields

Each technology in `data.ai.json` may now include:

| Field | Description |
|-------|-------------|
| `sourceCoverage` | Number of corroborating source families seen for the blip |
| `sourceFreshness` | Freshest/stalest observed evidence age in days |
| `evidenceSummary` | Compact summary of evidence sources and metrics |
| `whyThisRing` | One-line human explanation for the assigned ring |

Pipeline metadata also includes `meta.pipeline.runMetrics`, `ringQuality`, `quadrantQuality`, and `quadrantRingQuality`.

### Editorial Filtering

The radar distinguishes technologies from resource-like repositories. Popular GitHub collections such as awesome lists, books, roadmaps, prompt libraries, tutorials, and similar learning resources can still appear in review summaries, but they should not be treated as strong `adopt`/`trial` technology candidates by default.

The human review summary explicitly flags these leaks under `suspiciousItems.resourceLikeStrongRings` so operators can catch editorial mistakes even when technical thresholds pass.

### Provenance Fields

When provenance tracking is enabled, technology objects include optional source metadata:

| Field | Description |
|-------|-------------|
| `sourceSummary` | Human-readable summary of signal sources (e.g., "GitHub: 1.2k stars, HN: 45 pts") |
| `signalFreshness` | ISO timestamp of when external signals were collected |

These fields appear only when present—backward compatible with existing data files.

### Testing

```bash
# Run ETL tests
cd scripts && source ../.venv/bin/activate && python -m pytest tests -q

# Generate a human review summary for the current radar output
PYTHONPATH=scripts ./.venv/bin/python scripts/review_radar_output.py --input src/data/data.ai.json

# Verify dry-run
python scripts/main.py --dry-run

# Build frontend
npm run build
```

## Deployment

### GitHub Pages (Recommended)

1. Fork this repository
2. Go to Settings → Pages
3. Source: Deploy from a branch → Branch: `master`, Folder: `/ (root)`
4. The workflow will automatically build and deploy on every push

### Manual Deploy

```bash
npm run build
# Upload dist/ folder to your hosting provider
```

## Configuration

Edit `scripts/config.yaml` to customize:

- `github.min_stars`: Minimum stars for GitHub repos (default: 100)
- `hackernews.min_points`: Minimum HN points (default: 10)
- `radar.max_technologies`: Max technologies to track (default: 50)

## Contributing

1. Create a new branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run tests: `npm run lint && npm run build`
4. Push and create a PR

## License

MIT License - see LICENSE file for details.

---

**Made with ❤️ by Qualtio**
