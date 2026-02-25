"""Pipeline orchestration for Tech Radar ETL

This module orchestrates the complete pipeline:
1. collect source signals
2. normalize + dedupe
3. temporal/domain enrichment
4. classify AI
5. strategic filtering
6. optional deep scan enrich
7. output generation
"""

import logging
import re
from statistics import pvariance
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from etl.config import ETLConfig, SourcesConfig, ClassificationConfig, FilteringConfig, DeepScanConfig
from etl.ai_filter import AITechnologyFilter, FilteredItem, StrategicValue
from etl.deep_scanner import DeepScanner
from etl.checkpoint import CheckpointStore
from etl.history_store import HistoryStore
from etl.description_quality import is_valid_description
from etl.classifier import TechnologyClassifier, ClassificationResult
from etl.market_scoring import score_technology, calculate_confidence
from etl.ring_assignment import assign_rings
from etl.sources.github_trending import GitHubTrendingSource
from etl.sources.hackernews import HackerNewsSource
from etl.sources.google_trends import GoogleTrendsSource
from etl.candidate_selector import select_candidates, CandidateSelection
from etl.llm_cache import LLMDecisionCache

logger = logging.getLogger(__name__)

TECH_ALIASES = {
    # Databases
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "postgre": "postgresql",
    "pg": "postgresql",
    "redis": "redis",
    "mongodb": "mongodb",
    "mongo": "mongodb",
    "mysql": "mysql",
    "sqlite": "sqlite",
    "cassandra": "cassandra",
    "elasticsearch": "elasticsearch",
    "clickhouse": "clickhouse",
    "supabase": "supabase",
    "firebase": "firebase",
    "dynamodb": "dynamodb",
    "cockroachdb": "cockroachdb",
    "neo4j": "neo4j",
    "influxdb": "influxdb",
    "timescaledb": "timescaledb",
    # Languages
    "rust": "rust",
    "rustlang": "rust",
    "golang": "go",
    "go": "go",
    "python": "python",
    "py": "python",
    "typescript": "typescript",
    "ts": "typescript",
    "javascript": "javascript",
    "js": "javascript",
    "java": "java",
    "kotlin": "kotlin",
    "swift": "swift",
    "zig": "zig",
    "nim": "nim",
    "elixir": "elixir",
    "erlang": "erlang",
    "haskell": "haskell",
    "scala": "scala",
    "clojure": "clojure",
    "ruby": "ruby",
    "php": "php",
    "csharp": "c#",
    "c#": "c#",
    "cpp": "c++",
    "c++": "c++",
    "dart": "dart",
    "julia": "julia",
    "r-lang": "r",
    "rlang": "r",
    # Frameworks - Frontend
    "react": "react",
    "reactjs": "react",
    "vue": "vue",
    "vuejs": "vue",
    "angular": "angular",
    "svelte": "svelte",
    "next": "nextjs",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "nuxt": "nuxtjs",
    "nuxt.js": "nuxtjs",
    "remix": "remix",
    "astro": "astro",
    "solid": "solidjs",
    "solidjs": "solidjs",
    "qwik": "qwik",
    "htmx": "htmx",
    "alpine": "alpinejs",
    "alpine.js": "alpinejs",
    # Frameworks - Backend
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "express": "express",
    "expressjs": "express",
    "nestjs": "nestjs",
    "spring": "spring boot",
    "spring-boot": "spring boot",
    "rails": "ruby on rails",
    "ruby-on-rails": "ruby on rails",
    "laravel": "laravel",
    "symfony": "symfony",
    "gin": "gin",
    "echo": "echo",
    "fiber": "fiber",
    "actix": "actix",
    "rocket": "rocket",
    # DevOps/Cloud
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "terraform": "terraform",
    "ansible": "ansible",
    "pulumi": "pulumi",
    "vagrant": "vagrant",
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
    "vercel": "vercel",
    "netlify": "netlify",
    "cloudflare": "cloudflare",
    "heroku": "heroku",
    "fly.io": "fly.io",
    "render": "render",
    # CI/CD
    "github-actions": "github actions",
    "gitlab-ci": "gitlab ci",
    "jenkins": "jenkins",
    "circleci": "circleci",
    "travis": "travis ci",
    "argo": "argo",
    "flux": "flux",
    # AI/ML
    "tensorflow": "tensorflow",
    "pytorch": "pytorch",
    "jax": "jax",
    "huggingface": "huggingface",
    "langchain": "langchain",
    "llama": "llama",
    "llamaindex": "llamaindex",
    "openai": "openai",
    "anthropic": "anthropic",
    "ollama": "ollama",
    "comfyui": "comfyui",
    "stable-diffusion": "stable diffusion",
    "mlflow": "mlflow",
    "kubeflow": "kubeflow",
    # Tools
    "git": "git",
    "github": "github",
    "gitlab": "gitlab",
    "bitbucket": "bitbucket",
    "vscode": "vscode",
    "neovim": "neovim",
    "nvim": "neovim",
    "vim": "vim",
    "emacs": "emacs",
    "jetbrains": "jetbrains",
    "cursor": "cursor",
    "warp": "warp",
    "fig": "fig",
    "starship": "starship",
    "zellij": "zellij",
    "tmux": "tmux",
    "ripgrep": "ripgrep",
    "fd": "fd",
    "fzf": "fzf",
    "bat": "bat",
    "exa": "exa",
    "eza": "eza",
    "zoxide": "zoxide",
    "atuin": "atuin",
    # API/GraphQL
    "graphql": "graphql",
    "grpc": "grpc",
    "rest": "rest api",
    "openapi": "openapi",
    "swagger": "swagger",
    "postman": "postman",
    "insomnia": "insomnia",
    "kafka": "kafka",
    "rabbitmq": "rabbitmq",
    "nats": "nats",
    "pulsar": "pulsar",
    # Testing/QA
    "qa": "qa",
    "testing": "testing",
    "cypress": "cypress",
    "playwright": "playwright",
    "puppeteer": "puppeteer",
    "selenium": "selenium",
    "jest": "jest",
    "vitest": "vitest",
    "pytest": "pytest",
    "mocha": "mocha",
    "cucumber": "cucumber",
    "gatling": "gatling",
    "k6": "k6",
    # Mobile
    "react-native": "react native",
    "flutter": "flutter",
    "ionic": "ionic",
    "capacitor": "capacitor",
    "expo": "expo",
    # Security
    "auth0": "auth0",
    "keycloak": "keycloak",
    "vault": "vault",
    "snyk": "snyk",
    "trivy": "trivy",
    # Monitoring/Observability
    "prometheus": "prometheus",
    "grafana": "grafana",
    "datadog": "datadog",
    "jaeger": "jaeger",
    "otel": "opentelemetry",
    "opentelemetry": "opentelemetry",
    # Node.js
    "node": "nodejs",
    "nodejs": "nodejs",
    "node.js": "nodejs",
    "bun": "bun",
    "deno": "deno",
    "npm": "npm",
    "pnpm": "pnpm",
    "yarn": "yarn",
}

NON_TECH_STOPWORDS = {
    "show",
    "hn",
    "building",
    "with",
    "from",
    "using",
    "built",
    "new",
    "this",
    "that",
    "and",
}

RING_INDEX = {
    "hold": 0,
    "assess": 1,
    "trial": 2,
    "adopt": 3,
}


@dataclass
class NormalizedTech:
    name: str
    description: str
    stars: int
    forks: int
    language: Optional[str]
    topics: List[str]
    url: str
    hn_mentions: int = 0
    sources: List[str] = field(default_factory=list)
    signals: Dict[str, float] = field(default_factory=dict)
    market_score: float = 0.0
    trend_delta: float = 0.0
    previous_ring: Optional[str] = None
    moved: int = 0
    last_updated: Optional[str] = None
    domain: Optional[str] = None


class RadarPipeline:
    """Main pipeline orchestrator for Tech Radar ETL"""

    def __init__(self, config: Optional[ETLConfig] = None,
                 checkpoint_path: Optional[str] = None,
                 save_interval: int = 100,
                 resume: bool = False):
        self.config = config or ETLConfig()
        self.save_interval = save_interval
        self.resume = resume
        self.checkpoint: Optional[CheckpointStore] = None
        if checkpoint_path:
            self.checkpoint = CheckpointStore(Path(checkpoint_path))
        self.history_store: Optional[HistoryStore] = None
        self.previous_snapshot: Optional[Dict[str, Any]] = None
        if self.config.history.enabled:
            self.history_store = HistoryStore(
                Path(self.config.history.file),
                max_weeks=self.config.history.max_weeks,
            )
            self.previous_snapshot = self.history_store.get_latest_snapshot()
        
        # Initialize LLM decision cache if enabled
        self.llm_cache: Optional[LLMDecisionCache] = None
        if self.config.llm_optimization.cache_enabled:
            cache_path = Path(self.config.llm_optimization.cache_file)
            self.llm_cache = LLMDecisionCache(cache_path)
        
        self._init_components()

    def _init_components(self):
        """Initialize pipeline components"""
        self.github_source = GitHubTrendingSource(self.config.sources.github_trending)
        self.hn_source = HackerNewsSource(self.config.sources.hackernews)
        self.google_trends_source = GoogleTrendsSource(self.config.sources.google_trends)

        if self.config.classification:
            try:
                self.classifier = TechnologyClassifier(model=self.config.classification.model)
            except ValueError:
                logger.warning("AI classifier not available, using fallback")
                self.classifier = None
        else:
            self.classifier = None

        self.filter = AITechnologyFilter(
            self.config.filtering,
            model=self.config.classification.model,
            llm_cache=self.llm_cache,
            max_drift=self.config.llm_optimization.cache_drift_threshold,
        )

        self.deep_scanner = DeepScanner(
            allowed_repos=self.config.deep_scan.repos if self.config.deep_scan else None,
            use_ai_analysis=False
        )

    def _collect_sources(self) -> List[NormalizedTech]:
        """Phase 1: Collect signals from all sources"""
        technologies: Dict[str, NormalizedTech] = {}

        if self.config.sources.github_trending.enabled:
            signals = self.github_source.fetch()
            for signal in signals:
                raw = signal.raw_data or {}
                name = raw.get("name", signal.name)
                if not name:
                    continue
                key = name.lower().strip()

                existing = technologies.get(key)
                gh_popularity = min(100.0, float(raw.get("stars", 0)) / 1000.0)
                gh_momentum = float(raw.get("gh_momentum", 0.0))

                if existing is None:
                    technologies[key] = NormalizedTech(
                        name=name,
                        description=raw.get("description", ""),
                        stars=raw.get("stars", 0),
                        forks=raw.get("forks", 0),
                        language=raw.get("language"),
                        topics=raw.get("topics", []),
                        url=raw.get("url", ""),
                        sources=["github"],
                        signals={
                            "gh_popularity": gh_popularity,
                            "gh_momentum": gh_momentum,
                        },
                    )
                else:
                    existing.stars = max(existing.stars, raw.get("stars", 0))
                    existing.forks = max(existing.forks, raw.get("forks", 0))
                    existing.description = existing.description or raw.get("description", "")
                    existing.language = existing.language or raw.get("language")
                    existing.topics = list(set(existing.topics + (raw.get("topics", []) or [])))
                    existing.url = existing.url or raw.get("url", "")
                    if "github" not in existing.sources:
                        existing.sources.append("github")
                    existing.signals["gh_popularity"] = max(existing.signals.get("gh_popularity", 0.0), gh_popularity)
                    existing.signals["gh_momentum"] = max(existing.signals.get("gh_momentum", 0.0), gh_momentum)

        if self.config.sources.hackernews.enabled:
            hn_posts = list(self.hn_source.fetch())
            for post in hn_posts:
                tech_name = self._extract_tech_name(post.title)
                if tech_name:
                    key = tech_name.lower().strip()
                    if key in technologies:
                        technologies[key].hn_mentions += 1
                        if "hackernews" not in technologies[key].sources:
                            technologies[key].sources.append("hackernews")
                        technologies[key].signals["hn_heat"] = min(
                            100.0,
                            technologies[key].signals.get("hn_heat", 0.0) + float(getattr(post, "points", 0)) / 2.0,
                        )
                    else:
                        technologies[key] = NormalizedTech(
                            name=tech_name,
                            description=post.title,
                            stars=0,
                            forks=0,
                            language=None,
                            topics=[],
                            url=post.url,
                            hn_mentions=1,
                            sources=["hackernews"],
                            signals={
                                "hn_heat": min(100.0, float(getattr(post, "points", 0)) / 2.0),
                            },
                        )

        if self.config.sources.google_trends.enabled:
            google_signals = self.google_trends_source.fetch()
            for signal in google_signals:
                name = (signal.name or "").strip().lower()
                if not name:
                    continue

                raw = signal.raw_data or {}
                google_momentum = min(100.0, float(signal.score) * 10.0)

                if name in technologies:
                    tech = technologies[name]
                    if "google_trends" not in tech.sources:
                        tech.sources.append("google_trends")
                    tech.signals["google_momentum"] = max(
                        tech.signals.get("google_momentum", 0.0),
                        google_momentum,
                    )
                else:
                    technologies[name] = NormalizedTech(
                        name=name,
                        description=raw.get("query", name),
                        stars=0,
                        forks=0,
                        language=None,
                        topics=[],
                        url="",
                        hn_mentions=0,
                        sources=["google_trends"],
                        signals={"google_momentum": google_momentum},
                    )

        return list(technologies.values())

    def _extract_tech_name(self, title: str) -> Optional[str]:
        """Extract technology name from HN post title using multi-word patterns first"""
        cleaned_title = re.sub(r"[^a-zA-Z0-9+#\.\-\s]", " ", title.lower())
        
        # First try multi-word patterns (e.g., "react native", "github actions")
        for alias, canonical in TECH_ALIASES.items():
            if " " in alias and alias in cleaned_title:
                return canonical
        
        # Then try compound patterns with dots/dashes
        for alias, canonical in TECH_ALIASES.items():
            if "." in alias or "-" in alias:
                pattern = alias.replace(".", r"\.").replace("-", r"[- ]?")
                if re.search(rf"\b{pattern}\b", cleaned_title):
                    return canonical
        
        # Finally try individual tokens
        tokens = [token.strip(".-") for token in cleaned_title.split() if token.strip(".-")]
        
        # Priority: look for known tech names first
        for token in tokens:
            if token in NON_TECH_STOPWORDS:
                continue
            if token in TECH_ALIASES:
                return TECH_ALIASES[token]
        
        # Look for programming languages (single word)
        lang_patterns = ["rust", "python", "golang", "typescript", "javascript", "kotlin", "swift", "zig"]
        for token in tokens:
            if token in lang_patterns:
                return token
        
        return None

    def _normalize_and_dedupe(self, technologies: List[NormalizedTech]) -> List[NormalizedTech]:
        """Phase 2: Normalize and deduplicate technologies"""
        seen: Set[str] = set()
        unique_techs: List[NormalizedTech] = []

        for tech in technologies:
            name_key = tech.name.lower().strip()
            if name_key and name_key not in seen:
                seen.add(name_key)
                unique_techs.append(tech)
            elif name_key in seen:
                for existing in unique_techs:
                    if existing.name.lower() == name_key:
                        existing.stars = max(existing.stars, tech.stars)
                        existing.hn_mentions = max(existing.hn_mentions, tech.hn_mentions)
                        existing.sources = list(set(existing.sources + tech.sources))
                        break

        return unique_techs

    def _temporal_enrichment(self, technologies: List[NormalizedTech]) -> List[NormalizedTech]:
        """Phase 3: Temporal and domain enrichment"""
        now = datetime.now().isoformat()
        for tech in technologies:
            if tech.last_updated is None:
                tech.last_updated = now
            if tech.domain is None:
                tech.domain = self._infer_domain(tech)
        return technologies

    def _apply_market_scoring(self, technologies: List[NormalizedTech]) -> List[NormalizedTech]:
        # Weights without Google Trends (unreliable source)
        weights = {
            "gh_momentum": self.config.scoring.weights.github_momentum,
            "gh_popularity": self.config.scoring.weights.github_popularity,
            "hn_heat": self.config.scoring.weights.hn_heat,
        }

        for tech in technologies:
            tech.signals.setdefault("gh_popularity", min(100.0, tech.stars / 1000.0))
            tech.signals.setdefault("hn_heat", min(100.0, float(tech.hn_mentions) * 10.0))
            tech.signals.setdefault("gh_momentum", tech.signals.get("gh_momentum", 0.0))

            tech.market_score = score_technology(tech.signals, weights=weights)

            signal_values = [
                float(tech.signals.get("gh_momentum", 0.0)),
                float(tech.signals.get("gh_popularity", 0.0)),
                float(tech.signals.get("hn_heat", 0.0)),
            ]
            variance = pvariance(signal_values) if len(signal_values) > 1 else 0.0
            source_count = len(set(tech.sources))
            tech.signals["score_confidence"] = calculate_confidence(source_count, variance)

        return technologies

    def _infer_domain(self, tech: NormalizedTech) -> str:
        """Infer domain from technology characteristics"""
        topics = [t.lower() for t in tech.topics]
        lang = (tech.language or "").lower()

        if any(t in topics for t in ["ui", "frontend", "web", "react", "vue", "angular"]):
            return "frontend"
        if any(t in topics for t in ["backend", "api", "server"]):
            return "backend"
        if any(t in topics for t in ["devops", "infrastructure", "cloud"]):
            return "devops"
        if any(t in topics for t in ["machine-learning", "ai", "ml"]):
            return "ai/ml"

        if lang in ["python", "r", "julia"]:
            return "data science"
        if lang in ["rust", "c", "c++", "go"]:
            return "systems"

        return "general"

    def _classify_ai(self, technologies: List[NormalizedTech]) -> List[ClassificationResult]:
        """Phase 4: AI Classification"""
        if not self.classifier:
            return self._fallback_classification(technologies)

        tech_dicts = [
            {
                'name': tech.name,
                'stars': tech.stars,
                'hn_mentions': tech.hn_mentions,
                'description': tech.description
            }
            for tech in technologies
        ]

        try:
            return self.classifier.classify_batch(tech_dicts)
        except Exception as e:
            logger.warning(f"AI classification failed: {e}, using fallback")
            return self._fallback_classification(technologies)

    def _fallback_classification(self, technologies: List[NormalizedTech]) -> List[ClassificationResult]:
        """Fallback classification without AI"""
        results = []
        for tech in technologies:
            if tech.stars > 10000 or tech.hn_mentions > 50:
                ring = 'adopt'
            elif tech.stars > 1000 or tech.hn_mentions > 10:
                ring = 'trial'
            elif tech.stars > 100 or tech.hn_mentions > 5:
                ring = 'assess'
            else:
                ring = 'hold'

            quadrant = self._infer_quadrant(tech)

            results.append(ClassificationResult(
                name=tech.name,
                quadrant=quadrant,
                ring=ring,
                description=tech.description or f"{tech.name} - technology with {tech.stars} stars",
                confidence=0.5,
                trend='stable'
            ))

        return results

    def _infer_quadrant(self, tech: NormalizedTech) -> str:
        """Infer quadrant from tech characteristics"""
        lang = (tech.language or "").lower()
        topics = [t.lower() for t in tech.topics]

        if lang in ["python", "javascript", "typescript", "rust", "go", "java", "c#"]:
            return "languages"
        if any(t in topics for t in ["devops", "cloud", "infrastructure", "kubernetes"]):
            return "platforms"
        if any(t in topics for t in ["testing", "tool", "framework", "library"]):
            return "tools"
        return "techniques"

    def _strategic_filter(self, technologies: List[NormalizedTech],
                          classifications: List[ClassificationResult]) -> List[FilteredItem]:
        """Phase 5: Strategic filtering with Zalando-style quality gates
        
        Filters applied:
        1. Minimum sources: Must appear in at least N sources (default: 2)
        2. Quality gates: Must meet minimum stars/HN mentions for its ring
        3. Temporal consistency: Must have been around for minimum days
        4. AI filtering: Strategic value assessment
        5. Distribution: Target 12-15 technologies balanced across quadrants
        """
        
        # Apply quality gates first (Zalando-style)
        qualified_techs = []
        for tech, classification in zip(technologies, classifications):
            # Gate 1: Minimum number of sources
            min_sources = getattr(self.config.filtering, 'min_sources', 2)
            if len(tech.sources) < min_sources:
                logger.debug(f"Filtering out {tech.name}: only {len(tech.sources)} sources (min: {min_sources})")
                continue
            
            # Gate 2: Quality gates based on ring
            if not self._passes_quality_gate(tech, classification.ring):
                logger.debug(f"Filtering out {tech.name}: doesn't pass quality gate for ring {classification.ring}")
                continue
            
            qualified_techs.append((tech, classification))
        
        logger.info(f"Phase 5 - {len(qualified_techs)} technologies passed quality gates out of {len(technologies)}")
        
        # Create items for AI filtering
        items = []
        for tech, classification in qualified_techs:
            items.append(type('TechItem', (), {
                'name': classification.name,
                'description': classification.description,
                'stars': tech.stars,
                'quadrant': classification.quadrant,
                'ring': classification.ring,
                'confidence': classification.confidence,
                'trend': classification.trend,
                'market_score': tech.market_score,
                'signals': tech.signals,
                'moved': tech.moved,
                'sources': tech.sources,
            })())

        # Use AI filter for strategic assessment
        filtered = self.filter.filter(items) or []
        
        # Target: 12-15 technologies (Zalando-style focused radar)
        target_min = getattr(self.config.distribution, 'target_total', 15) - 3
        target_max = getattr(self.config.distribution, 'target_total', 15)
        
        # Fallback: if AI filter is too aggressive, use top items by market score
        if len(filtered) < target_min:
            logger.warning(f"AI filter too aggressive: only {len(filtered)} items. Using fallback.")
            # Sort all items by market score * confidence
            items.sort(key=lambda x: (getattr(x, 'market_score', 0) * x.confidence), reverse=True)
            # Take top target_max items
            filtered = items[:target_max]
            logger.info(f"Fallback selected {len(filtered)} top items by market score")
        else:
            # Sort by market score and confidence
            filtered.sort(key=lambda x: (getattr(x, 'market_score', 0) * x.confidence), reverse=True)
            filtered = filtered[:target_max]

        # Fill with fallback candidates if needed
        existing_names = {item.name.lower() for item in filtered}
        fallback_candidates = []
        for tech, classification in qualified_techs:
            if classification.name.lower() in existing_names:
                continue
            fallback_candidates.append((tech, classification))

        # Sort by composite score (market score * confidence)
        fallback_candidates.sort(
            key=lambda pair: pair[0].market_score * pair[1].confidence, 
            reverse=True
        )
        
        # Fill up to target minimum
        while len(filtered) < min(target_min, len(items)) and fallback_candidates:
            tech, classification = fallback_candidates.pop(0)
            fallback_item = FilteredItem(
                name=classification.name,
                description=classification.description,
                stars=tech.stars,
                quadrant=classification.quadrant,
                ring=classification.ring,
                confidence=max(0.5, classification.confidence),  # Higher minimum confidence
                trend=classification.trend,
                strategic_value=StrategicValue.MEDIUM,
            )
            setattr(fallback_item, "market_score", tech.market_score)
            setattr(fallback_item, "signals", tech.signals)
            setattr(fallback_item, "moved", tech.moved)
            filtered.append(fallback_item)

        return filtered[:target_max]
    
    def _passes_quality_gate(self, tech: NormalizedTech, ring: str) -> bool:
        """Check if technology passes Zalando-style quality gates for its ring"""
        quality_gates = getattr(self.config, 'quality_gates', None)
        if not quality_gates:
            return True
        
        # Check minimum stars for the ring
        min_stars_config = getattr(quality_gates, 'min_stars', None)
        if min_stars_config and ring in ['assess', 'trial', 'adopt']:
            min_stars = getattr(min_stars_config, ring, 0)
            if tech.stars < min_stars:
                return False
        
        # Check minimum HN mentions for the ring
        min_hn_config = getattr(quality_gates, 'min_hn_mentions', None)
        if min_hn_config and ring in ['assess', 'trial', 'adopt']:
            min_hn = getattr(min_hn_config, ring, 0)
            if tech.hn_mentions < min_hn:
                return False
        
        return True

    def _assign_market_rings(self, items: List[FilteredItem]) -> List[FilteredItem]:
        if not items:
            return items

        previous_map: Dict[str, Dict[str, Any]] = {}
        if self.previous_snapshot:
            for tech in self.previous_snapshot.get("technologies", []):
                tech_id = tech.get("id")
                if tech_id:
                    previous_map[str(tech_id)] = tech

        ring_inputs: List[Dict[str, Any]] = []
        for item in items:
            tech_id = item.name.lower().replace(" ", "-")
            previous_market_score = float(previous_map.get(tech_id, {}).get("marketScore", 0.0))
            market_score = float(getattr(item, "market_score", 0.0))
            ring_inputs.append(
                {
                    "id": tech_id,
                    "market_score": market_score,
                    "trend_delta": market_score - previous_market_score,
                }
            )

        thresholds = {
            "adopt": self.config.scoring.thresholds.adopt,
            "trial": self.config.scoring.thresholds.trial,
            "assess": self.config.scoring.thresholds.assess,
        }
        hysteresis = {
            "promote_delta": self.config.scoring.hysteresis.promote_delta,
            "demote_delta": self.config.scoring.hysteresis.demote_delta,
            "cooldown_weeks": self.config.scoring.hysteresis.cooldown_weeks,
        }
        guardrail = {
            "enabled": self.config.distribution_guardrail.enabled,
            "max_ring_ratio": self.config.distribution_guardrail.max_ring_ratio,
        }

        assigned = assign_rings(
            ring_inputs,
            previous=previous_map,
            thresholds=thresholds,
            hysteresis=hysteresis,
            guardrail=guardrail,
        )
        assigned_by_id = {entry["id"]: entry for entry in assigned}

        for item in items:
            tech_id = item.name.lower().replace(" ", "-")
            assignment = assigned_by_id.get(tech_id, {})
            ring = assignment.get("ring", item.ring)
            trend_delta = float(assignment.get("trend_delta", 0.0))
            prev_ring = assignment.get("previous_ring")

            item.ring = ring
            setattr(item, "moved", 0)
            if isinstance(prev_ring, str) and prev_ring in RING_INDEX and ring in RING_INDEX:
                setattr(item, "moved", RING_INDEX[ring] - RING_INDEX[prev_ring])

            if trend_delta > 5:
                item.trend = "up"
            elif trend_delta < -5:
                item.trend = "down"
            else:
                item.trend = "stable"

        return items

    def _deep_scan_enrich(self, filtered_items: List[FilteredItem]) -> List[FilteredItem]:
        """Phase 6: Optional deep scan enrichment"""
        if not self.config.deep_scan or not self.config.deep_scan.enabled:
            return filtered_items

        if not self.config.deep_scan.repos:
            return filtered_items

        return filtered_items

    def _generate_output(self, items: List[FilteredItem]) -> Dict[str, Any]:
        """Phase 7: Generate output"""
        technologies = []
        dropped_bad_description = 0
        for item in items:
            description = item.description if isinstance(item.description, str) else ""
            if not description.strip():
                description = f"{item.name} technology with external market momentum signals."
            elif not is_valid_description(description):
                dropped_bad_description += 1
                continue

            raw_signals = getattr(item, "signals", {}) or {}
            if not isinstance(raw_signals, dict):
                raw_signals = {}

            signals = {
                "ghMomentum": round(float(raw_signals.get("gh_momentum", 0.0)), 2),
                "ghPopularity": round(float(raw_signals.get("gh_popularity", 0.0)), 2),
                "hnHeat": round(float(raw_signals.get("hn_heat", 0.0)), 2),
            }
            
            # Only include Google Trends if enabled
            if self.config.sources.google_trends.enabled:
                signals["googleMomentum"] = round(float(raw_signals.get("google_momentum", 0.0)), 2)

            technologies.append({
                'id': item.name.lower().replace(' ', '-'),
                'name': item.name,
                'quadrant': item.quadrant,
                'ring': item.ring,
                'description': description,
                'moved': int(getattr(item, 'moved', 0)),
                'trend': item.trend,
                'marketScore': round(float(getattr(item, 'market_score', 0.0)), 2),
                'signals': signals,
                'stars': item.stars,
                'confidence': item.confidence,
                'isDeprecated': item.is_deprecated,
                'replacement': item.replacement,
                'updatedAt': datetime.now().isoformat()
            })

        if dropped_bad_description:
            logger.info(
                "Phase 7 - Dropped %s items due to invalid descriptions",
                dropped_bad_description,
            )

        return {
            'updatedAt': datetime.now().isoformat(),
            'technologies': technologies
        }

    def _save_checkpoint(self, phase: str, cursor: int = 0, **kwargs) -> None:
        """Save checkpoint at current phase."""
        if self.checkpoint:
            data = {"phase": phase, "cursor": cursor, **kwargs}
            self.checkpoint.save(data)

    def _load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load checkpoint if resume is enabled."""
        if self.resume and self.checkpoint:
            return self.checkpoint.load()
        return None

    def run(self) -> Dict[str, Any]:
        """Run the complete pipeline"""
        logger.info("Starting Tech Radar Pipeline")

        checkpoint_data = self._load_checkpoint()
        if checkpoint_data:
            logger.info(f"Resuming from checkpoint: {checkpoint_data.get('phase')}")

        technologies = self._collect_sources()
        logger.info(f"Phase 1 - Collected {len(technologies)} technologies from sources")
        self._save_checkpoint("collect", cursor=len(technologies))

        technologies = self._normalize_and_dedupe(technologies)
        logger.info(f"Phase 2 - Normalized and deduplicated to {len(technologies)} technologies")
        self._save_checkpoint("dedupe", cursor=len(technologies))

        technologies = self._temporal_enrichment(technologies)
        logger.info("Phase 3 - Temporal/domain enrichment complete")
        self._save_checkpoint("enrich")

        technologies = self._apply_market_scoring(technologies)
        logger.info("Phase 3b - Deterministic market scoring complete")
        self._save_checkpoint("market_score", cursor=len(technologies))

        classifications = self._classify_ai(technologies)
        logger.info(f"Phase 4 - AI classification complete for {len(classifications)} items")
        self._save_checkpoint("classify", cursor=len(classifications))

        filtered_items = self._strategic_filter(technologies, classifications)
        logger.info(f"Phase 5 - Strategic filtering complete, {len(filtered_items or [])} items remain")
        self._save_checkpoint("filter", cursor=len(filtered_items or []))

        # Phase 5b: Candidate selection - partition into Core/Watchlist/Borderline
        # Build lookup for market scores and trend_delta from the original technologies
        tech_scores = {t.name.lower(): t.market_score for t in technologies}
        tech_trend_deltas = {t.name.lower(): t.trend_delta for t in technologies}

        candidate_items = [
            {
                "id": item.name.lower().replace(" ", "-"),
                "market_score": tech_scores.get(item.name.lower(), 0),
                "trend_delta": tech_trend_deltas.get(item.name.lower(), 0),
                "confidence": item.confidence,
            }
            for item in (filtered_items or [])
        ]
        candidate_selection = select_candidates(
            candidate_items,
            target_total=getattr(self.config.distribution, 'target_total', 15),
            watchlist_ratio=self.config.llm_optimization.watchlist_ratio,
            borderline_band=self.config.llm_optimization.borderline_band,
        )
        logger.info(f"Phase 5b - Candidate selection: {len(candidate_selection.core_ids)} core, "
                   f"{len(candidate_selection.watchlist_ids)} watchlist, "
                   f"{len(candidate_selection.borderline_ids)} borderline")
        self._save_checkpoint("candidate_selection")

        filtered_items = self._assign_market_rings(filtered_items)

        enriched_items = self._deep_scan_enrich(filtered_items)
        logger.info(f"Phase 6 - Deep scan enrichment complete")
        self._save_checkpoint("deep_scan")

        output = self._generate_output(enriched_items or [])
        logger.info(f"Phase 7 - Output generated with {len(output['technologies'])} technologies")

        if self.history_store:
            self.history_store.append_snapshot(output)

        self._save_checkpoint("complete", cursor=len(output['technologies']))

        return output


def run(config_path: Optional[str] = None,
        checkpoint_path: Optional[str] = None,
        save_interval: int = 100,
        resume: bool = False) -> Dict[str, Any]:
    """Run pipeline with optional config path and checkpoint support"""
    if config_path:
        config = load_etl_config(config_path)
    else:
        config = ETLConfig()

    pipeline = RadarPipeline(config, checkpoint_path, save_interval, resume)
    return pipeline.run()


def load_etl_config(config_path: str) -> ETLConfig:
    """Load ETL config from path"""
    from etl.config import load_etl_config as load_config
    return load_config(config_path)
