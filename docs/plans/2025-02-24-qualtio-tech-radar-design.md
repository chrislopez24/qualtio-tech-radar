# Qualtio Tech Radar - Design Document

**Date**: 2025-02-24  
**Status**: Approved  
**Author**: AI Assistant  

## 1. Overview

Interactive Technology Radar with AI-powered automatic updates, inspired by ThoughtWorks Technology Radar but with enhanced visual design and automated trend detection.

### Key Features
- **4 Quadrants**: Techniques, Tools, Platforms, Languages & Frameworks
- **4 Rings**: Adopt, Trial, Assess, Hold
- **Dual Mode**: Manual curated view + AI-generated view
- **Auto-updates**: Weekly automated analysis from multiple sources
- **Modern UI**: Professional, performant, and visually stunning

## 2. Technology Stack

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + Framer Motion
- **Visualization**: Custom D3.js implementation
- **UI Components**: Radix UI + shadcn/ui
- **Icons**: Lucide React

### Backend/Data
- **Data Collection**: Python scripts
- **AI Engine**: Synthetic API (OpenAI-compatible)
- **Data Storage**: JSON files in repository
- **Automation**: GitHub Actions (weekly cron job)

### External APIs
- **GitHub Trends API**: Trending repositories, stars, forks
- **Hacker News API**: Popular tech discussions
- **Google Trends**: Search interest data
- **Synthetic API**: AI classification and analysis (https://api.synthetic.new/openai/v1)

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Repository                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │   Next.js App    │  │  Python Scripts  │                │
│  │                  │  │                  │                │
│  │  ┌────────────┐  │  │  ┌────────────┐  │                │
│  │  │  Radar UI  │  │  │  │  Scraper   │  │                │
│  │  │  (D3.js)   │  │  │  │   Module   │  │                │
│  │  └────────────┘  │  │  └────────────┘  │                │
│  │                  │  │                  │                │
│  │  ┌────────────┐  │  │  ┌────────────┐  │                │
│  │  │  Search &  │  │  │  │  AI        │  │                │
│  │  │  Filters   │  │  │  │  Analyzer  │  │                │
│  │  └────────────┘  │  │  └────────────┘  │                │
│  │                  │  │                  │                │
│  └──────────────────┘  └──────────────────┘                │
│           │                       │                          │
│           └───────────┬───────────┘                          │
│                       │                                      │
│              ┌────────┴────────┐                             │
│              │   JSON Data     │                             │
│              │   Files         │                             │
│              └─────────────────┘                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  GitHub Actions (Weekly)                     │
├─────────────────────────────────────────────────────────────┤
│  1. Run Python scraper                                       │
│  2. Analyze with Synthetic API                               │
│  3. Generate data.ai.json                                    │
│  4. Commit & Push                                            │
│  5. Trigger GitHub Pages rebuild                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Pages                             │
│              (Static Site Hosting)                           │
└─────────────────────────────────────────────────────────────┘
```

## 4. Data Sources & AI Analysis

### Data Collection Strategy

#### 1. GitHub Trends
- **API**: GitHub REST API + GitHub Trending scraper
- **Metrics**: Stars (weekly growth), forks, contributors, activity
- **Scope**: Top 100 trending repos per language/category

#### 2. Hacker News
- **API**: Algolia HN Search API
- **Query**: Tech-related posts with >100 points
- **Timeframe**: Past 7 days

#### 3. Google Trends
- **Tool**: pytrends (unofficial API)
- **Terms**: Predefined list of technologies + detected new terms
- **Metrics**: Search interest over time

#### 4. Synthetic API Analysis
- **Endpoint**: https://api.synthetic.new/openai/v1/chat/completions
- **Models**: Llama 3.3, Mixtral, or Qwen (cost-effective)
- **Tasks**:
  - Classify technology into quadrant
  - Determine ring placement (Adopt/Trial/Assess/Hold)
  - Generate description
  - Analyze trend direction

### AI Classification Prompt

```
Analyze the following technology trend data and classify:

Technology: {name}
GitHub Stars: {stars}
Hacker News Mentions: {mentions}
Google Trends Score: {trend_score}
Description: {description}

Classify into:
1. Quadrant: Techniques | Tools | Platforms | Languages & Frameworks
2. Ring: Adopt | Trial | Assess | Hold
3. Provide a 2-3 sentence description
4. Trend: Growing | Stable | Declining

Respond in JSON format.
```

## 5. Visual Design System

### Color Palette
```css
/* Rings */
--ring-adopt: #10B981;    /* Emerald 500 */
--ring-trial: #3B82F6;    /* Blue 500 */
--ring-assess: #F59E0B;   /* Amber 500 */
--ring-hold: #EF4444;     /* Red 500 */

/* Quadrants */
--quad-techniques: #8B5CF6;      /* Violet 500 */
--quad-tools: #06B6D4;           /* Cyan 500 */
--quad-platforms: #EC4899;       /* Pink 500 */
--quad-languages: #84CC16;       /* Lime 500 */

/* UI */
--bg-primary: #0F172A;      /* Slate 900 */
--bg-secondary: #1E293B;    /* Slate 800 */
--text-primary: #F8FAFC;    /* Slate 50 */
--text-secondary: #94A3B8;  /* Slate 400 */
```

### Radar Visualization

#### Technical Approach
- **Library**: D3.js v7 with React integration
- **Pattern**: Custom SVG-based radar with force layout for positioning
- **Interactivity**:
  - Hover: Highlight blip + show tooltip
  - Click: Open detail panel
  - Zoom: D3 zoom behavior
  - Filter: By quadrant, ring, or search term

#### Visual Features
1. **Animated Entry**: Blips fade in with stagger animation
2. **Pulse Effect**: New/updated technologies pulse gently
3. **Smooth Transitions**: Between manual and AI mode
4. **Glassmorphism**: Control panels with backdrop blur
5. **Responsive**: Adapts to mobile, tablet, desktop

### UI Components

#### Main Layout
```
┌─────────────────────────────────────────────────────┐
│  Logo    Search...           [Manual ▼] [Theme]    │
├─────────────────────────────────────────────────────┤
│                                                     │
│              ┌─────────────────┐                   │
│              │                 │                   │
│   ┌──────────┤    RADAR        ├──────────┐       │
│   │          │   (Center)      │          │       │
│   │          │                 │          │       │
│   │          └─────────────────┘          │       │
│   │                                       │       │
│   │  Quadrant Labels                      │       │
│   │                                       │       │
│   └───────────────────────────────────────┘       │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [Legend] [Export SVG] [Last Updated: 2 days ago]  │
└─────────────────────────────────────────────────────┘
```

#### Detail Panel (Slide-over)
- Technology name + icon
- Current ring badge
- Quadrant label
- Description
- Trend chart (mini sparkline)
- Related technologies
- Source links

## 6. Data Structure

### Manual Data (`data.json`)
```json
{
  "version": "2025-02-24",
  "mode": "manual",
  "technologies": [
    {
      "id": "react",
      "name": "React",
      "quadrant": "languages-frameworks",
      "ring": "adopt",
      "description": "Industry standard for building user interfaces.",
      "lastUpdated": "2025-01-15"
    }
  ]
}
```

### AI Data (`data.ai.json`)
```json
{
  "version": "2025-02-24",
  "mode": "ai",
  "generatedAt": "2025-02-24T10:00:00Z",
  "sources": ["github", "hackernews", "google-trends"],
  "technologies": [
    {
      "id": "shadcn-ui",
      "name": "shadcn/ui",
      "quadrant": "tools",
      "ring": "trial",
      "description": "Component library built on Radix UI and Tailwind.",
      "trend": "growing",
      "metrics": {
        "githubStars": 85000,
        "hnMentions": 45,
        "trendScore": 85
      },
      "confidence": 0.92
    }
  ]
}
```

## 7. File Structure

```
qualtio-tech-radar/
├── .github/
│   └── workflows/
│       └── weekly-update.yml     # GitHub Actions workflow
├── app/
│   ├── page.tsx                  # Main page
│   ├── layout.tsx                # Root layout
│   ├── globals.css               # Global styles
│   ├── components/
│   │   ├── Radar.tsx             # Main radar visualization
│   │   ├── Blip.tsx              # Individual tech blip
│   │   ├── Quadrant.tsx          # Quadrant section
│   │   ├── DetailPanel.tsx       # Slide-over detail view
│   │   ├── SearchBar.tsx         # Search input
│   │   ├── ModeToggle.tsx        # Manual/AI mode switch
│   │   ├── Legend.tsx            # Ring color legend
│   │   └── FilterBar.tsx         # Filter controls
│   ├── hooks/
│   │   ├── useRadarData.ts       # Data fetching hook
│   │   └── useBlipPosition.ts    # D3 positioning logic
│   └── lib/
│       ├── data.ts               # Data loading utilities
│       └── utils.ts              # Helper functions
├── components/
│   └── ui/                       # shadcn/ui components
├── scripts/
│   ├── scraper/
│   │   ├── github.py             # GitHub API client
│   │   ├── hackernews.py         # HN API client
│   │   └── trends.py             # Google Trends scraper
│   ├── ai/
│   │   └── classifier.py         # Synthetic API integration
│   └── main.py                   # Entry point
├── data/
│   ├── data.json                 # Manual curated data
│   └── data.ai.json              # AI-generated data
├── public/
│   └── logos/                    # Tech logos
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## 8. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Setup Next.js project with TypeScript
- [ ] Install dependencies (D3, Tailwind, Radix)
- [ ] Create base layout and theme
- [ ] Implement static radar visualization

### Phase 2: Core Features (Week 2)
- [ ] Build radar with D3.js
- [ ] Add blip positioning logic
- [ ] Implement interactivity (hover, click)
- [ ] Create detail panel component

### Phase 3: Data Integration (Week 3)
- [ ] Build Python scrapers
- [ ] Integrate Synthetic API
- [ ] Create GitHub Actions workflow
- [ ] Test data generation pipeline

### Phase 4: Polish & Deploy (Week 4)
- [ ] Add search and filters
- [ ] Implement manual/AI mode toggle
- [ ] Optimize performance
- [ ] Deploy to GitHub Pages
- [ ] Add documentation

## 9. Performance Considerations

### Frontend
- **Lazy Loading**: Load radar data on demand
- **Memoization**: React.memo for blip components
- **Virtualization**: For large technology lists
- **Image Optimization**: Next.js Image component

### Data Pipeline
- **Caching**: Cache API responses (Redis/memory)
- **Rate Limiting**: Respect GitHub API limits
- **Incremental Updates**: Only fetch changes since last run
- **Parallel Processing**: Async scrapers

## 10. Success Metrics

- **Update Frequency**: Weekly automated updates
- **Load Time**: < 2 seconds initial load
- **Interactivity**: 60fps animations
- **Data Quality**: > 90% accurate classifications
- **Coverage**: > 200 technologies tracked

## 11. Future Enhancements

- [ ] Historical trend visualization
- [ ] Technology comparison tool
- [ ] Export to PDF/PowerPoint
- [ ] Team collaboration features
- [ ] Custom quadrant/ring configuration
- [ ] Integration with internal systems

---

## Approval

This design has been reviewed and approved for implementation.
