"""Pipeline orchestration for Tech Radar ETL

This module orchestrates the complete pipeline:
1. collect source signals
2. normalize + dedupe
3. temporal/domain enrichment
4. classify AI
5. strategic filtering
6. output generation
"""

import logging
import os
import re
from statistics import pvariance
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from etl.config import ETLConfig, load_etl_config
from etl.ai_filter import (
    AITechnologyFilter,
    FilteredItem,
    StrategicValue,
    is_resource_like_repository,
    is_strong_ring_editorially_eligible,
    is_trial_ring_editorially_eligible,
)
from etl.checkpoint import CheckpointStore
from etl.history_store import HistoryStore
from etl.description_quality import is_valid_description
from etl.classifier import TechnologyClassifier, ClassificationResult
from etl.market_scoring import calculate_confidence, score_technology, scale_signal_logarithmically
from etl.ring_assignment import assign_rings
from etl.sources.github_trending import GitHubTrendingSource
from etl.sources.hackernews import HackerNewsSource
from etl.candidate_selector import select_candidates, CandidateSelection
from etl.llm_cache import LLMDecisionCache
from etl.quadrant_logic import infer_quadrant, quadrant_affinity
from etl.selection_logic import strategic_filter, build_watchlist_items

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

RADAR_QUADRANTS = ("techniques", "platforms", "tools", "languages")


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
    # Canonical entity fields for Radar V2
    canonical_id: Optional[str] = None
    entity_type: str = "technology"
    evidence: List[dict] = field(default_factory=list)


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
            # Buffer writes during run, flush once at the end for better ETL throughput.
            self.llm_cache = LLMDecisionCache(cache_path, auto_flush=False)

        self._last_filter_stats: Dict[str, int] = {
            "classified": 0,
            "qualified": 0,
            "ai_accepted": 0,
            "rejected_low_sources": 0,
            "rejected_quality_gate": 0,
            "rejected_ai_filter": 0,
        }
        self._last_llm_calls: int = 0
        
        self._init_components()

    def _init_components(self):
        """Initialize pipeline components"""
        self.github_source = GitHubTrendingSource(self.config.sources.github_trending)
        self.hn_source = HackerNewsSource(self.config.sources.hackernews)

        configured_model = self.config.classification.model
        effective_model = os.environ.get("SYNTHETIC_MODEL", configured_model)

        if self.config.classification:
            try:
                self.classifier = TechnologyClassifier(model=effective_model)
            except ValueError:
                logger.warning("AI classifier not available, using fallback")
                self.classifier = None
        else:
            self.classifier = None

        self.filter = AITechnologyFilter(
            self.config.filtering,
            model=effective_model,
            llm_cache=self.llm_cache,
            max_drift=self.config.llm_optimization.cache_drift_threshold,
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
        # Supported external signals: GitHub adoption plus Hacker News buzz.
        weights = {
            "gh_momentum": self.config.scoring.weights.github_momentum,
            "gh_popularity": self.config.scoring.weights.github_popularity,
            "hn_heat": self.config.scoring.weights.hn_heat,
        }

        previous_scores: Dict[str, float] = {}
        if self.previous_snapshot:
            for entry in self.previous_snapshot.get("technologies", []):
                if not isinstance(entry, dict):
                    continue
                tech_id = str(entry.get("id", "")).strip().lower()
                if not tech_id:
                    continue
                previous_scores[tech_id] = float(entry.get("marketScore", 0.0))

        for tech in technologies:
            tech.signals.setdefault(
                "gh_popularity",
                scale_signal_logarithmically(float(tech.stars), 250000.0, 100.0),
            )
            tech.signals.setdefault("hn_heat", min(100.0, float(tech.hn_mentions) * 10.0))
            tech.signals.setdefault("gh_momentum", tech.signals.get("gh_momentum", 0.0))

            signal_values = [
                float(tech.signals.get("gh_momentum", 0.0)),
                float(tech.signals.get("gh_popularity", 0.0)),
                float(tech.signals.get("hn_heat", 0.0)),
            ]
            variance = pvariance(signal_values) if len(signal_values) > 1 else 0.0
            source_count = len(set(tech.sources))
            tech.market_score = score_technology(
                tech.signals,
                weights=weights,
                source_count=source_count,
                github_stars=float(tech.stars),
                github_forks=float(tech.forks),
            )
            tech.signals["score_confidence"] = calculate_confidence(source_count, variance)

            tech_id = tech.name.lower().replace(" ", "-")
            prev_score = previous_scores.get(tech_id)
            tech.trend_delta = tech.market_score - prev_score if prev_score is not None else 0.0

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

    def _classify_selective(
        self,
        technologies: List[NormalizedTech],
        candidate_selection,
    ) -> List[ClassificationResult]:
        """Phase 4b: Selective LLM classification

        Only borderline candidates get LLM classification.
        Core and watchlist candidates use deterministic fallback.
        """
        # Build lookup by ID
        tech_by_id = {t.name.lower().replace(" ", "-"): t for t in technologies}

        # Initialize results
        all_classifications: List[ClassificationResult] = []
        self._last_llm_calls = 0

        # Process core candidates with deterministic classification (no LLM)
        core_techs = [tech_by_id[tid] for tid in candidate_selection.core_ids if tid in tech_by_id]
        if core_techs:
            logger.debug(f"Classifying {len(core_techs)} core candidates deterministically")
            core_classifications = self._fallback_classification(core_techs)
            for c in core_classifications:
                c.confidence = min(0.9, c.confidence)  # High confidence for core
            all_classifications.extend(core_classifications)

        # Process watchlist candidates with deterministic classification (no LLM)
        watchlist_techs = [tech_by_id[tid] for tid in candidate_selection.watchlist_ids if tid in tech_by_id]
        if watchlist_techs:
            logger.debug(f"Classifying {len(watchlist_techs)} watchlist candidates deterministically")
            watchlist_classifications = self._fallback_classification(watchlist_techs)
            for c in watchlist_classifications:
                c.confidence = min(0.8, c.confidence)  # Good confidence for watchlist
                c.trend = "up"  # Watchlist items are trending up
            all_classifications.extend(watchlist_classifications)

        # Process borderline candidates with LLM (selective)
        borderline_techs = [tech_by_id[tid] for tid in candidate_selection.borderline_ids if tid in tech_by_id]
        if borderline_techs and self.config.llm_optimization.enabled:
            # Enforce budget
            budget_remaining = self.config.llm_optimization.max_calls_per_run
            if budget_remaining <= 0:
                logger.warning("LLM budget exhausted, using fallback for borderline candidates")
                borderline_classifications = self._fallback_classification(borderline_techs)
            else:
                logger.info(f"Classifying {len(borderline_techs)} borderline candidates via LLM "
                           f"(budget: {budget_remaining})")
                borderline_classifications = self._classify_borderline_batch(borderline_techs, budget_remaining)
            all_classifications.extend(borderline_classifications)
        elif borderline_techs:
            # LLM optimization disabled, use fallback
            logger.debug(f"Classifying {len(borderline_techs)} borderline candidates deterministically")
            borderline_classifications = self._fallback_classification(borderline_techs)
            all_classifications.extend(borderline_classifications)

        return all_classifications

    def _classify_borderline_batch(
        self,
        borderline_techs: List[NormalizedTech],
        budget_remaining: int,
    ) -> List[ClassificationResult]:
        """Classify borderline candidates using LLM with budget enforcement."""
        if not self.classifier:
            return self._fallback_classification(borderline_techs)

        # Respect budget - prioritize by uncertainty (lower confidence first)
        prioritized = sorted(borderline_techs, key=lambda t: t.signals.get("score_confidence", 0.5))
        to_classify = prioritized[:budget_remaining]

        if len(to_classify) < len(borderline_techs):
            logger.warning(f"Budget limited: classifying {len(to_classify)} of {len(borderline_techs)} "
                          f"borderline candidates via LLM")

        tech_dicts = [
            {
                'name': tech.name,
                'stars': tech.stars,
                'hn_mentions': tech.hn_mentions,
                'description': tech.description
            }
            for tech in to_classify
        ]

        try:
            self._last_llm_calls += len(to_classify)
            llm_classifications = self.classifier.classify_batch(tech_dicts)

            # For items that exceeded budget, use fallback
            fallback_techs = [t for t in borderline_techs if t not in to_classify]
            if fallback_techs:
                fallback_classifications = self._fallback_classification(fallback_techs)
                # Merge results
                return llm_classifications + fallback_classifications

            return llm_classifications
        except Exception as e:
            logger.warning(f"AI classification failed: {e}, using fallback for borderline")
            return self._fallback_classification(borderline_techs)

    def _classify_ai(self, technologies: List[NormalizedTech]) -> List[ClassificationResult]:
        """Phase 4: AI Classification (legacy - used for non-selective mode)"""
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
            self._last_llm_calls = len(technologies)
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
                description=tech.description or f"{tech.name} technology with measurable adoption and market momentum signals.",
                confidence=0.5,
                trend='stable'
            ))

        return results

    def _infer_quadrant(self, tech: NormalizedTech) -> str:
        """Infer quadrant from tech characteristics"""
        return infer_quadrant(tech)

    def _quadrant_affinity(self, tech: NormalizedTech, target_quadrant: str) -> float:
        """Score how naturally a technology fits a target quadrant."""
        return quadrant_affinity(tech, target_quadrant, self._infer_domain)

    def _normalize_id(self, name: str) -> str:
        return str(name).lower().replace(" ", "-").strip()

    def _to_strategic_value(self, value: Any) -> StrategicValue:
        if isinstance(value, StrategicValue):
            return value
        normalized = str(value or "medium").lower().strip()
        if normalized == "high":
            return StrategicValue.HIGH
        if normalized == "low":
            return StrategicValue.LOW
        return StrategicValue.MEDIUM

    def _build_filtered_item(
        self,
        tech: NormalizedTech,
        classification: ClassificationResult,
        confidence_floor: float = 0.5,
    ) -> FilteredItem:
        item = FilteredItem(
            name=classification.name,
            description=classification.description,
            stars=tech.stars,
            quadrant=classification.quadrant,
            ring=classification.ring,
            confidence=max(confidence_floor, classification.confidence),
            trend=classification.trend,
            strategic_value=self._to_strategic_value(getattr(classification, "strategic_value", "medium")),
            is_deprecated=False,
            replacement=None,
        )
        setattr(item, "market_score", tech.market_score)
        setattr(item, "signals", tech.signals)
        setattr(item, "moved", tech.moved)
        setattr(item, "sources", tech.sources)
        setattr(item, "topics", getattr(tech, "topics", []))
        return item

    def _strategic_filter(self, technologies: List[NormalizedTech],
                          classifications: List[ClassificationResult]) -> List[FilteredItem]:
        """Phase 5: Quality-gated filtering and balanced selection."""
        return strategic_filter(self, technologies, classifications, RADAR_QUADRANTS)

    def _build_watchlist_items(
        self,
        technologies: List[NormalizedTech],
        classifications: List[ClassificationResult],
        candidate_selection: CandidateSelection,
        main_ids: Optional[Set[str]] = None,
    ) -> List[FilteredItem]:
        """Build a dedicated watchlist section separate from the main radar blips."""
        return build_watchlist_items(self, technologies, classifications, candidate_selection, main_ids)
    
    def _passes_quality_gate(self, tech: NormalizedTech, ring: str) -> bool:
        """Check if technology passes Zalando-style quality gates for its ring"""
        quality_gates = getattr(self.config, 'quality_gates', None)
        if not quality_gates:
            return True

        if ring not in ['assess', 'trial', 'adopt']:
            return True

        # Use OR semantics (stars or HN evidence) to avoid over-pruning.
        stars_pass = True
        min_stars_config = getattr(quality_gates, 'min_stars', None)
        if min_stars_config:
            min_stars = getattr(min_stars_config, ring, 0)
            stars_pass = tech.stars >= min_stars

        hn_pass = True
        min_hn_config = getattr(quality_gates, 'min_hn_mentions', None)
        if min_hn_config:
            min_hn = getattr(min_hn_config, ring, 0)
            hn_pass = tech.hn_mentions >= min_hn

        return stars_pass or hn_pass

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
            previous_entry = previous_map.get(tech_id)
            market_score = float(getattr(item, "market_score", 0.0))
            trend_delta = 0.0
            if previous_entry is not None:
                previous_market_score = float(previous_entry.get("marketScore", 0.0))
                trend_delta = market_score - previous_market_score
            ring_inputs.append(
                {
                    "id": tech_id,
                    "market_score": market_score,
                    "trend_delta": trend_delta,
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
            "min_ring_count": self.config.distribution.min_per_ring,
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

            if ring in {"adopt", "trial"} and is_resource_like_repository(item.name, item.description):
                ring = "assess"
            elif ring == "adopt" and not is_strong_ring_editorially_eligible(
                item.name,
                item.description,
                getattr(item, "topics", []),
            ):
                ring = "assess"
            elif ring == "trial" and not is_trial_ring_editorially_eligible(
                item.name,
                item.description,
                getattr(item, "topics", []),
            ):
                ring = "assess"

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

    def _generate_output(
        self,
        items: List[FilteredItem],
        watchlist_items: Optional[List[FilteredItem]] = None,
    ) -> Dict[str, Any]:
        """Phase 6: Generate output"""

        repaired_bad_description = 0

        def _serialize(blips: List[FilteredItem]) -> List[Dict[str, Any]]:
            nonlocal repaired_bad_description
            payload: List[Dict[str, Any]] = []

            for item in blips:
                description = item.description if isinstance(item.description, str) else ""
                if not description.strip():
                    description = f"{item.name} technology with external market momentum signals."
                elif not is_valid_description(description):
                    repaired_bad_description += 1
                    description = f"{item.name} technology tracked for current relevance and market momentum."

                raw_signals = getattr(item, "signals", {}) or {}
                if not isinstance(raw_signals, dict):
                    raw_signals = {}

                signals = {
                    "ghMomentum": round(float(raw_signals.get("gh_momentum", 0.0)), 2),
                    "ghPopularity": round(float(raw_signals.get("gh_popularity", 0.0)), 2),
                    "hnHeat": round(float(raw_signals.get("hn_heat", 0.0)), 2),
                }

                payload.append({
                    'id': self._normalize_id(item.name),
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
                    'isDeprecated': bool(getattr(item, 'is_deprecated', False)),
                    'replacement': getattr(item, 'replacement', None),
                    'updatedAt': datetime.now().isoformat()
                })

            return payload

        technologies = _serialize(items)
        watchlist = _serialize(watchlist_items or [])

        if repaired_bad_description:
            logger.info("Phase 6 - Repaired %s invalid descriptions", repaired_bad_description)

        previous_technologies = (
            (self.previous_snapshot or {}).get("technologies", [])
            if isinstance((self.previous_snapshot or {}).get("technologies", []), list)
            else []
        )
        previous_by_id = {
            str(entry.get("id")): entry
            for entry in previous_technologies
            if isinstance(entry, dict) and entry.get("id")
        }
        current_ids = {str(entry.get("id")) for entry in technologies if isinstance(entry, dict) and entry.get("id")}

        ring_distribution = {ring: 0 for ring in ("adopt", "trial", "assess", "hold")}
        for entry in technologies:
            ring = str(entry.get("ring", ""))
            if ring in ring_distribution:
                ring_distribution[ring] += 1

        def _is_github_only_signal(entry: Dict[str, Any]) -> bool:
            signals = entry.get("signals", {})
            if not isinstance(signals, dict):
                return False
            gh_momentum = float(signals.get("ghMomentum", 0.0) or 0.0)
            gh_popularity = float(signals.get("ghPopularity", 0.0) or 0.0)
            hn_heat = float(signals.get("hnHeat", 0.0) or 0.0)
            has_github_signal = gh_momentum > 0.0 or gh_popularity > 0.0
            return has_github_signal and hn_heat <= 0.0

        def _quality_snapshot(entries: List[Dict[str, Any]], *, strong_ring: Optional[str] = None) -> Dict[str, Any]:
            count = len(entries)
            if count == 0:
                return {
                    "count": 0,
                    "avgMarketScore": 0.0,
                    "githubOnlyRatio": 0.0,
                    "resourceLikeCount": 0,
                    "editoriallyWeakCount": 0,
                    "topSuspicious": [],
                    "status": "good",
                }

            github_only_entries: List[Dict[str, Any]] = []
            top_suspicious: List[Dict[str, Any]] = []
            resource_like_count = 0
            editorially_weak_count = 0

            for entry in entries:
                reasons: List[str] = []
                description = str(entry.get("description", ""))
                entry_id = str(entry.get("id", ""))
                effective_ring = strong_ring or str(entry.get("ring", ""))
                if _is_github_only_signal(entry):
                    github_only_entries.append(entry)
                    reasons.append("githubOnly")
                if is_resource_like_repository(entry_id, description):
                    resource_like_count += 1
                    reasons.append("resourceLike")
                elif effective_ring == "adopt" and not is_strong_ring_editorially_eligible(
                    str(entry.get("name", "")),
                    description,
                    [],
                ):
                    editorially_weak_count += 1
                    reasons.append("editoriallyWeak")
                elif effective_ring == "trial" and not is_trial_ring_editorially_eligible(
                    str(entry.get("name", "")),
                    description,
                    [],
                ):
                    editorially_weak_count += 1
                    reasons.append("editoriallyWeak")

                if reasons:
                    top_suspicious.append(
                        {
                            "id": entry_id,
                            "name": str(entry.get("name", "")),
                            "marketScore": round(float(entry.get("marketScore", 0.0) or 0.0), 2),
                            "reasons": reasons,
                        }
                    )

            avg_market_score = round(
                sum(float(entry.get("marketScore", 0.0) or 0.0) for entry in entries) / count,
                2,
            )
            github_only_ratio = round(len(github_only_entries) / count, 4)
            top_suspicious.sort(key=lambda entry: float(entry.get("marketScore", 0.0)), reverse=True)

            status = "good"
            if strong_ring in {"adopt", "trial"}:
                strong_ring_low_score = (
                    strong_ring == "adopt" and avg_market_score < 80.0
                ) or (
                    strong_ring == "trial" and avg_market_score < 60.0
                )
                if (
                    github_only_ratio >= 0.5
                    or resource_like_count > 0
                    or editorially_weak_count > 0
                    or strong_ring_low_score
                ):
                    status = "bad"
            elif github_only_ratio >= 0.5 or resource_like_count > 0 or editorially_weak_count > 0:
                status = "warn"

            return {
                "count": count,
                "avgMarketScore": avg_market_score,
                "githubOnlyRatio": github_only_ratio,
                "resourceLikeCount": resource_like_count,
                "editoriallyWeakCount": editorially_weak_count,
                "topSuspicious": top_suspicious[:5],
                "status": status,
            }

        def _ring_quality(entries: List[Dict[str, Any]], ring: str) -> Dict[str, Any]:
            ring_entries = [entry for entry in entries if str(entry.get("ring", "")) == ring]
            return _quality_snapshot(ring_entries, strong_ring=ring)

        quadrant_names = ("platforms", "techniques", "tools", "languages")
        ring_names = ("adopt", "trial", "assess", "hold")

        quadrant_quality = {
            quadrant: (
                _quality_snapshot([entry for entry in technologies if str(entry.get("quadrant", "")) == quadrant])
                if any(str(entry.get("quadrant", "")) == quadrant for entry in technologies)
                else {
                    "count": 0,
                    "avgMarketScore": 0.0,
                    "githubOnlyRatio": 0.0,
                    "resourceLikeCount": 0,
                    "editoriallyWeakCount": 0,
                    "topSuspicious": [],
                    "status": "missing",
                }
            )
            for quadrant in quadrant_names
        }

        quadrant_ring_quality = {
            quadrant: {
                ring: (
                    _quality_snapshot(
                        [
                            entry
                            for entry in technologies
                            if str(entry.get("quadrant", "")) == quadrant and str(entry.get("ring", "")) == ring
                        ],
                        strong_ring=ring,
                    )
                    if any(
                        str(entry.get("quadrant", "")) == quadrant and str(entry.get("ring", "")) == ring
                        for entry in technologies
                    )
                    else {
                        "count": 0,
                        "avgMarketScore": 0.0,
                        "githubOnlyRatio": 0.0,
                        "resourceLikeCount": 0,
                        "editoriallyWeakCount": 0,
                        "topSuspicious": [],
                        "status": "missing",
                    }
                )
                for ring in ring_names
            }
            for quadrant in quadrant_names
        }

        def _sample(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            ranked = sorted(
                entries,
                key=lambda entry: float(entry.get("marketScore", 0.0) or 0.0),
                reverse=True,
            )
            return [
                {
                    "id": str(entry.get("id", "")),
                    "name": str(entry.get("name", "")),
                    "ring": str(entry.get("ring", "")),
                    "marketScore": round(float(entry.get("marketScore", 0.0) or 0.0), 2),
                }
                for entry in ranked[:5]
                if entry.get("id")
            ]

        top_added = _sample(
            [
                entry
                for entry in technologies
                if isinstance(entry, dict) and entry.get("id") and str(entry.get("id")) not in previous_by_id
            ]
        )
        top_dropped = _sample(
            [
                entry
                for entry_id, entry in previous_by_id.items()
                if entry_id not in current_ids
            ]
        )

        return {
            'updatedAt': datetime.now().isoformat(),
            'technologies': technologies,
            'watchlist': watchlist,
            'meta': {
                'pipeline': {
                    'droppedInvalidDescriptions': 0,
                    'repairedDescriptions': repaired_bad_description,
                    'rejectedByStage': {
                        'insufficientSources': int(self._last_filter_stats.get("rejected_low_sources", 0)),
                        'qualityGate': int(self._last_filter_stats.get("rejected_quality_gate", 0)),
                        'aiFilter': int(self._last_filter_stats.get("rejected_ai_filter", 0)),
                    },
                    'ringDistribution': ring_distribution,
                    'ringQuality': {
                        ring: _ring_quality(technologies, ring)
                        for ring in ("adopt", "trial", "assess", "hold")
                    },
                    'quadrantQuality': quadrant_quality,
                    'quadrantRingQuality': quadrant_ring_quality,
                    'topAdded': top_added,
                    'topDropped': top_dropped,
                }
            }
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
        collected_count = len(technologies)
        logger.info(f"Phase 1 - Collected {len(technologies)} technologies from sources")
        self._save_checkpoint("collect", cursor=len(technologies))

        technologies = self._normalize_and_dedupe(technologies)
        normalized_count = len(technologies)
        logger.info(f"Phase 2 - Normalized and deduplicated to {len(technologies)} technologies")
        self._save_checkpoint("dedupe", cursor=len(technologies))

        technologies = self._temporal_enrichment(technologies)
        logger.info("Phase 3 - Temporal/domain enrichment complete")
        self._save_checkpoint("enrich")

        technologies = self._apply_market_scoring(technologies)
        logger.info("Phase 3b - Deterministic market scoring complete")
        self._save_checkpoint("market_score", cursor=len(technologies))

        candidate_items = [
            {
                "id": t.name.lower().replace(" ", "-"),
                "market_score": t.market_score,
                "trend_delta": t.trend_delta,
                "confidence": t.signals.get("score_confidence", 0.5),
            }
            for t in technologies
        ]
        candidate_selection = select_candidates(
            candidate_items,
            target_total=getattr(self.config.distribution, 'target_total', 15),
            watchlist_ratio=self.config.llm_optimization.watchlist_ratio,
            borderline_band=self.config.llm_optimization.borderline_band,
        )
        logger.info(f"Phase 4 - Candidate selection: {len(candidate_selection.core_ids)} core, "
                   f"{len(candidate_selection.watchlist_ids)} watchlist, "
                   f"{len(candidate_selection.borderline_ids)} borderline")
        self._save_checkpoint("candidate_selection")

        classifications = self._classify_selective(
            technologies,
            candidate_selection,
        )
        classified_count = len(classifications)
        logger.info(f"Phase 4b - Selective AI classification complete for {len(classifications)} items "
                   f"({len(candidate_selection.borderline_ids)} borderline via LLM)")
        self._save_checkpoint("classify", cursor=len(classifications))

        filtered_items = self._strategic_filter(technologies, classifications)
        logger.info(f"Phase 5 - Strategic filtering complete, {len(filtered_items or [])} items remain")
        self._save_checkpoint("filter", cursor=len(filtered_items or []))

        filtered_items = self._assign_market_rings(filtered_items)

        watchlist_items = self._build_watchlist_items(
            technologies,
            classifications,
            candidate_selection,
            main_ids={self._normalize_id(item.name) for item in filtered_items},
        )
        watchlist_items = self._assign_market_rings(watchlist_items)

        output = self._generate_output(filtered_items or [], watchlist_items)
        output_count = len(output['technologies'])
        watchlist_count = len(output.get('watchlist', []))
        logger.info(
            "Phase 6 - Output generated with %s technologies and %s watchlist items",
            output_count,
            watchlist_count,
        )

        output.setdefault("meta", {})
        output["meta"].setdefault("pipeline", {})
        output["meta"]["pipeline"].update(
            {
                "collected": collected_count,
                "normalized": normalized_count,
                "candidatesCore": len(candidate_selection.core_ids),
                "candidatesWatchlist": len(candidate_selection.watchlist_ids),
                "candidatesBorderline": len(candidate_selection.borderline_ids),
                "classified": classified_count,
                "llmCalls": self._last_llm_calls,
                "qualified": self._last_filter_stats.get("qualified", 0),
                "output": output_count,
                "watchlist": watchlist_count,
            }
        )

        if self.history_store:
            self.history_store.append_snapshot(output)

        if self.llm_cache:
            self.llm_cache.flush()

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
