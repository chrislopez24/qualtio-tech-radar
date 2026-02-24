# Qualtio Tech Radar

AI-powered Technology Radar with automated weekly updates from GitHub Trends, Hacker News, and Google Trends using Synthetic API for classification.

![Tech Radar Preview](./docs/preview.png)

## Features

- **Interactive Radar Visualization**: Custom D3.js-based radar with 4 quadrants and 4 rings
- **Dual Mode**: Manual curation mode + AI-powered auto-classification mode
- **Glassmorphism UI**: Modern, responsive design with dark theme support
- **Automated Data Pipeline**: Weekly updates via GitHub Actions
- **Search & Filter**: Real-time search across all technologies

## Tech Stack

- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS + Framer Motion
- **Visualization**: D3.js
- **UI Components**: shadcn/ui
- **Data Pipeline**: Python 3.12 + Synthetic API

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
│   └── data/             # Technology data (JSON)
├── scripts/              # Python data pipeline
│   ├── scraper/          # GitHub & HN scrapers
│   ├── ai/               # AI classifier
│   └── main.py           # Pipeline entry point
├── .github/workflows/    # CI/CD automation
└── docs/                 # Documentation
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build static export for production |
| `npm run lint` | Run ESLint |
| `npm start` | Start production server (after build) |

## Data Pipeline (Optional)

To run the data collection pipeline locally:

```bash
# Ensure you have .env.local configured with API keys
python scripts/main.py
```

This will:
1. Fetch trending repos from GitHub
2. Collect tech posts from Hacker News
3. Classify technologies using Synthetic API
4. Generate `src/data/data.ai.json`

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
