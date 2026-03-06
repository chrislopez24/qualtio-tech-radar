# Qualtio Tech Radar

AI-powered Technology Radar with automated weekly updates from GitHub and Hacker News. Rings are assigned by deterministic market momentum (with hysteresis and guardrails) to avoid collapse into a single ring.

![Tech Radar Preview](./docs/preview.png)

## Features

- **Interactive Radar Visualization**: Custom D3.js-based radar with 4 quadrants and 4 rings
- **AI-Only Radar**: AI-powered classification and weekly refresh pipeline
- **Selective LLM Optimization**: 70%+ reduction in LLM calls via intelligent candidate selection (core/watchlist/borderline)
- **Drift-Aware Caching**: Reuse LLM decisions across runs with automatic invalidation
- **Shadow Quality Evaluation**: Validate optimized pipeline against baseline with pass/warn/fail quality gate outcomes
- **Operational Explainability**: Shadow evaluation reports with leader transition visibility and "what changed" insights
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
# Optional - only for running data pipeline locally
GITHUB_TOKEN=your_github_token_here
SYNTHETIC_API_KEY=your_synthetic_api_key_here
SYNTHETIC_API_URL=https://api.synthetic.new/v1
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

The ETL pipeline collects external technology signals from GitHub and Hacker News, classifies them using AI, and generates the radar data files. It does not perform a secondary repository deep-scan pass.

### Quick Start

```bash
# Ensure you have .env.local configured with API keys
source .venv/bin/activate
python scripts/main.py
```

This will:
1. Fetch external signals from GitHub and Hacker News
2. Compute deterministic market scores per technology
3. Assign rings using thresholds + hysteresis + distribution guardrails
4. Classify quadrants/descriptions with Synthetic API support
5. Generate `src/data/data.ai.json` and `src/data/data.ai.history.json`

### Environment Variables

Required for running the pipeline:

| Variable | Description | Required |
|----------|-------------|----------|
| `GH_TOKEN` | GitHub personal access token for API rate limits | Yes |
| `SYNTHETIC_API_KEY` | API key for Synthetic (LLM) classification | Yes |
| `SYNTHETIC_MODEL` | Model to use (default: `hf:MiniMaxAI/MiniMax-M2.5`) | No |
| `SYNTHETIC_API_URL` | Synthetic API endpoint (default: `https://api.synthetic.new/v1`) | No |

Use `SYNTHETIC_MODEL` to switch models (for example, `hf:moonshotai/Kimi-K2.5` for evaluation runs). Keep `SYNTHETIC_API_URL` unchanged unless your environment explicitly requires a different endpoint.

### Source Toggles

Enable/disable data sources in `scripts/config.yaml`:

```yaml
sources:
  github_trending:
    enabled: true   # Set to false to skip
  hackernews:
    enabled: true   # Set to false to skip
```

Or via CLI:
```bash
python scripts/main.py --sources github_trending,hackernews
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
