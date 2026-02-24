# Qualtio Tech Radar - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an AI-powered Technology Radar with automated weekly updates from GitHub Trends, Hacker News, and Google Trends using Synthetic API for classification.

**Architecture:** Static Next.js site hosted on GitHub Pages with Python data collection scripts running via GitHub Actions weekly. Custom D3.js radar visualization with glassmorphism UI design.

**Tech Stack:** Next.js 15 + TypeScript + Tailwind CSS + D3.js + Python + Synthetic API

---

## Prerequisites

Before starting, ensure you have:
- Node.js 20+ installed
- Python 3.11+ installed
- Synthetic API key (get from https://synthetic.new)
- Git configured

---

## Phase 1: Project Setup & Foundation (Tasks 1-5)

### Task 1: Initialize Next.js Project

**Step 1:** Create Next.js app
```bash
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

**Step 2:** Install dependencies
```bash
npm install d3 framer-motion lucide-react @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-slot class-variance-authority clsx tailwind-merge
npm install -D @types/d3
```

**Step 3:** Initialize shadcn/ui
```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button dialog input badge card separator tooltip sheet dropdown-menu
```

**Step 4:** Test and commit
```bash
npm run dev
git add .
git commit -m "chore: initial Next.js project setup with shadcn/ui"
```

---

### Task 2: Configure Theme

**Files:**
- Modify: `tailwind.config.ts`
- Modify: `app/globals.css`

**Step 1:** Add custom colors and dark theme
**Step 2:** Test build
**Step 3:** Commit

---

### Task 3: Create Types & Sample Data

**Files:**
- Create: `app/lib/types.ts`
- Create: `data/data.json`

**Types:** Quadrant, Ring, Mode, Trend, Technology, AITechnology, RadarData

**Step 1:** Write TypeScript interfaces
**Step 2:** Create sample data with 12 technologies
**Step 3:** Commit

---

### Task 4: Create Radar Configuration

**Files:**
- Create: `app/lib/radar-config.ts`

**Configuration:**
- QUADRANTS: 4 quadrants with colors and angles
- RINGS: 4 rings with colors and radii
- RADAR_SIZE: 800px

**Step 1:** Define constants
**Step 2:** Commit

---

### Task 5: Create Custom Hooks

**Files:**
- Create: `app/hooks/useRadarData.ts`
- Create: `app/hooks/useBlipPosition.ts`

**Hooks:**
- useRadarData: Fetch data.json or data.ai.json based on mode
- useBlipPosition: Deterministic positioning within quadrants/rings

**Step 1:** Implement hooks
**Step 2:** Test
**Step 3:** Commit

---

## Phase 2: UI Components (Tasks 6-11)

### Task 6: Create Radar Components

**Files:**
- Create: `app/components/Blip.tsx`
- Create: `app/components/Radar.tsx`

**Features:**
- SVG-based radar with quadrants and rings
- Animated blips with Framer Motion
- Hover and click interactions
- Search filtering

**Step 1:** Implement Radar visualization
**Step 2:** Add Blip component with animations
**Step 3:** Test interactions
**Step 4:** Commit

---

### Task 7: Create Detail Panel

**Files:**
- Create: `app/components/DetailPanel.tsx`

**Features:**
- Slide-over panel using shadcn Sheet
- Technology details (name, ring, quadrant, description)
- AI metrics (trend, GitHub stars, HN mentions, confidence)
- Responsive design

**Step 1:** Implement DetailPanel
**Step 2:** Test
**Step 3:** Commit

---

### Task 8: Create Header Components

**Files:**
- Create: `app/components/Header.tsx`
- Create: `app/components/ModeToggle.tsx`
- Create: `app/components/SearchBar.tsx`

**Features:**
- Sticky header with glassmorphism
- Logo and title
- Search input
- Mode toggle (Manual/AI)
- GitHub link

**Step 1:** Implement Header, ModeToggle, SearchBar
**Step 2:** Test
**Step 3:** Commit

---

### Task 9: Create Legend

**Files:**
- Create: `app/components/Legend.tsx`

**Features:**
- Ring color legend
- Quadrant color legend
- Responsive layout

**Step 1:** Implement Legend
**Step 2:** Commit

---

### Task 10: Integrate Main Page

**Files:**
- Modify: `app/page.tsx`
- Modify: `app/layout.tsx`

**Features:**
- Full page integration
- Mode switching
- Search filtering
- Detail panel display
- Loading and error states

**Step 1:** Update page.tsx with all components
**Step 2:** Update layout.tsx with metadata
**Step 3:** Test full app
**Step 4:** Commit

---

### Task 11: Build & Configure Static Export

**Files:**
- Modify: `next.config.js`

**Step 1:** Configure static export
```javascript
const nextConfig = {
  output: 'export',
  distDir: 'dist',
  images: {
    unoptimized: true
  }
}
```

**Step 2:** Test build
```bash
npm run build
```

**Step 3:** Commit

---

## Phase 3: Python Data Pipeline (Tasks 12-16)

### Task 12: Setup Python Environment

**Files:**
- Create: `scripts/requirements.txt`
- Create: `.env.example`
- Modify: `.gitignore`

**Dependencies:**
- requests
- python-dotenv
- pygithub
- openai

**Step 1:** Create requirements.txt
**Step 2:** Create .env.example
**Step 3:** Update .gitignore
**Step 4:** Commit

---

### Task 13: Create GitHub Scraper

**Files:**
- Create: `scripts/scraper/github.py`

**Features:**
- Fetch trending repositories
- Get repository details (stars, forks, language, topics)
- Handle rate limiting

**Step 1:** Implement GitHubScraper class
**Step 2:** Test with GITHUB_TOKEN
**Step 3:** Commit

---

### Task 14: Create Hacker News Scraper

**Files:**
- Create: `scripts/scraper/hackernews.py`

**Features:**
- Search technology-related posts
- Filter by date and points
- Categorize by tech category (frontend, backend, AI, etc.)

**Step 1:** Implement HackerNewsScraper class
**Step 2:** Test
**Step 3:** Commit

---

### Task 15: Create AI Classifier

**Files:**
- Create: `scripts/ai/classifier.py`

**Features:**
- Use Synthetic API (OpenAI-compatible)
- Classify technology into quadrant and ring
- Generate description
- Calculate confidence score

**Model:** llama-3.3-70b (cost-effective)

**Step 1:** Implement TechnologyClassifier class
**Step 2:** Test with sample data
**Step 3:** Commit

---

### Task 16: Create Main Pipeline

**Files:**
- Create: `scripts/main.py`
- Create: `scripts/config.yaml`

**Pipeline:**
1. Load configuration
2. Run GitHub scraper
3. Run HN scraper
4. Deduplicate technologies
5. Classify with AI
6. Generate data.ai.json
7. Save results

**Step 1:** Implement main pipeline
**Step 2:** Test locally
**Step 3:** Commit

---

## Phase 4: Automation & Deployment (Tasks 17-18)

### Task 17: Create GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/weekly-update.yml`

**Workflow:**
- Runs every Monday at 9:00 AM UTC
- Sets up Python environment
- Installs dependencies
- Runs data pipeline
- Commits data.ai.json
- Triggers GitHub Pages rebuild

**Step 1:** Create workflow file
**Step 2:** Test manually
**Step 3:** Commit

---

### Task 18: Deploy to GitHub Pages

**Step 1:** Push to GitHub
```bash
git push origin main
```

**Step 2:** Configure GitHub Pages
- Go to Settings > Pages
- Select "Deploy from a branch"
- Select "main" branch, "/dist" folder
- Save

**Step 3:** Wait for deployment
- Check Actions tab for build status
- Access site at https://yourusername.github.io/qualtio-tech-radar

**Step 4:** Verify
- Test manual mode
- Test AI mode (after first workflow run)
- Test search and filtering
- Test responsive design

---

## Verification Checklist

### Frontend
- [ ] Radar displays correctly with 4 quadrants and 4 rings
- [ ] Blips animate on load
- [ ] Hover highlights blips
- [ ] Click opens detail panel
- [ ] Search filters technologies
- [ ] Mode toggle switches between manual/AI
- [ ] Responsive on mobile/tablet/desktop
- [ ] Dark theme works correctly

### Backend
- [ ] GitHub scraper returns trending repos
- [ ] HN scraper returns tech posts
- [ ] AI classifier categorizes correctly
- [ ] Pipeline generates valid data.ai.json

### Automation
- [ ] GitHub Actions runs successfully
- [ ] Weekly schedule triggers correctly
- [ ] data.ai.json is committed and deployed

---

## Success Criteria

- ✅ Static site loads in < 2 seconds
- ✅ Radar is interactive and performant (60fps)
- ✅ Data updates automatically every week
- ✅ AI classifications are > 90% accurate
- ✅ Supports 100+ technologies
- ✅ Mobile-friendly design

---

## Plan Complete

This plan provides step-by-step instructions to build the Qualtio Tech Radar.

**Ready for execution!**

Choose execution approach:
1. **Subagent-Driven** (this session) - Fresh subagent per task
2. **Parallel Session** (separate) - New session with executing-plans
