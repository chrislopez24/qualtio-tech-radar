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
from time import perf_counter
from statistics import pvariance
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from etl.config import ETLConfig, load_etl_config
from etl.ai_filter import (
    AITechnologyFilter,
    DEPRECATED_MAP,
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
from etl.market_scoring import calculate_confidence, score_technology_breakdown, scale_signal_logarithmically
from etl.ring_policy import decide_ring
from etl.source_registry import build_source_registry
from etl.run_metrics import RunMetrics
from etl.artifact_quality import build_artifact_quality
from etl.canonical_mapping import deps_dev_subject_for, pypistats_subject_for
from etl.sources.github_trending import GitHubTrendingSource
from etl.sources.hackernews import HackerNewsSource
from etl.sources.deps_dev import DepsDevSource
from etl.sources.stackexchange import StackExchangeSource as StackExchangeEvidenceSource
from etl.sources.pypistats import PyPIStatsSource
from etl.sources.osv_source import OSVSource
from etl.candidate_selector import select_candidates, CandidateSelection
from etl.llm_cache import LLMDecisionCache
from etl.quadrant_logic import infer_quadrant, quadrant_affinity
from etl.selection_logic import strategic_filter, build_watchlist_items, rebalance_soft_ring_targets
from etl.evidence import EvidenceRecord

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
    evidence: list[EvidenceRecord] = field(default_factory=list)


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
        self._last_selection_candidates: List[FilteredItem] = []
        self.run_metrics = RunMetrics()
        
        self._init_components()

    def _init_components(self):
        """Initialize pipeline components"""
        self.source_registry = build_source_registry(
            self.config,
            github_cls=GitHubTrendingSource,
            hackernews_cls=HackerNewsSource,
            deps_dev_cls=DepsDevSource,
            stackexchange_cls=StackExchangeEvidenceSource,
            pypistats_cls=PyPIStatsSource,
            osv_cls=OSVSource,
        )
        self.github_source = self.source_registry.github_trending
        self.hn_source = self.source_registry.hackernews
        self.deps_dev_source = self.source_registry.deps_dev
        self.stackexchange_source = self.source_registry.stackexchange
        self.pypistats_source = self.source_registry.pypistats
        self.osv_source = self.source_registry.osv

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
            started = perf_counter()
            signals = self.github_source.fetch()
            self.run_metrics.record_source("github_trending", len(signals), perf_counter() - started)
            for signal in signals:
                raw = signal.raw_data or {}
                name = raw.get("name", signal.name)
                if not name:
                    continue
                key = name.lower().strip()

                existing = technologies.get(key)
                gh_popularity = scale_signal_logarithmically(float(raw.get("stars", 0)), 250000.0, 100.0)
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
            started = perf_counter()
            hn_posts = list(self.hn_source.fetch())
            self.run_metrics.record_source("hackernews", len(hn_posts), perf_counter() - started)
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
            if tech.canonical_id is None:
                tech.canonical_id = self._normalize_id(tech.name)
            if not tech.entity_type:
                tech.entity_type = "technology"
        return technologies

    def _attach_external_evidence(self, technologies: List[NormalizedTech]) -> List[NormalizedTech]:
        """Phase 3a: Attach external evidence records from optional sources."""
        tech_records: dict[str, list[EvidenceRecord]] = {
            self._normalize_id(tech.name): list(getattr(tech, "evidence", []) or [])
            for tech in technologies
        }
        candidate_techs = self._prioritize_external_evidence_candidates(technologies)

        def _merge_records(target_key: str, records: List[EvidenceRecord]) -> None:
            existing = tech_records.setdefault(target_key, [])
            existing.extend(records)
            deduped: list[EvidenceRecord] = []
            seen: set[tuple[str, str, str]] = set()
            for record in existing:
                dedupe_key = (record.source, record.metric, record.subject_id)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                deduped.append(record)
            tech_records[target_key] = deduped

        if self.config.sources.stackexchange.enabled:
            stack_subjects = [
                self._normalize_id(tech.name)
                for tech in candidate_techs[: self.config.sources.stackexchange.request_budget]
                if self._normalize_id(tech.name)
            ]
            stack_records = self._safe_fetch_evidence(self.stackexchange_source, list(dict.fromkeys(stack_subjects)))
            for record in stack_records:
                _merge_records(self._normalize_id(record.subject_id), [record])

        pypi_subject_map: dict[str, list[str]] = {}
        deps_subject_map: dict[str, list[str]] = {}
        for tech in candidate_techs:
            tech_key = self._normalize_id(tech.name)
            if not self._looks_like_package_name(tech.name):
                continue

            for subject in self._pypistats_subjects_for(tech):
                pypi_subject_map.setdefault(subject, []).append(tech_key)

            for subject in self._deps_dev_subjects_for(tech):
                deps_subject_map.setdefault(subject, []).append(tech_key)

        if self.config.sources.pypistats.enabled:
            pypi_subjects = list(pypi_subject_map.keys())[: self.config.sources.pypistats.request_budget]
            pypi_records = self._safe_fetch_evidence(self.pypistats_source, pypi_subjects)
            for record in pypi_records:
                for tech_key in pypi_subject_map.get(str(record.subject_id), []):
                    _merge_records(tech_key, [record])

        if self.config.sources.deps_dev.enabled:
            deps_subjects = list(deps_subject_map.keys())[: self.config.sources.deps_dev.request_budget]
            deps_records = self._safe_fetch_evidence(self.deps_dev_source, deps_subjects)
            for record in deps_records:
                subject_id = str(record.subject_id)
                subject_key = subject_id.split("@", 1)[0]
                for tech_key in deps_subject_map.get(subject_key, []):
                    _merge_records(tech_key, [record])

        osv_subject_map: dict[str, list[str]] = {}
        for tech in technologies:
            tech_key = self._normalize_id(tech.name)
            tech.evidence = tech_records.get(tech_key, [])
            for subject in self._osv_subjects_for(tech):
                osv_subject_map.setdefault(subject, []).append(tech_key)

        if self.config.sources.osv.enabled:
            osv_records = self._safe_fetch_evidence(self.osv_source, list(osv_subject_map.keys()))
            for record in osv_records:
                for tech_key in osv_subject_map.get(str(record.subject_id), []):
                    _merge_records(tech_key, [record])

        for tech in technologies:
            tech.evidence = tech_records.get(self._normalize_id(tech.name), [])

        return technologies

    def _prioritize_external_evidence_candidates(self, technologies: List[NormalizedTech]) -> List[NormalizedTech]:
        min_score = max(35.0, float(self.config.scoring.thresholds.assess) - 5.0)
        ranked: list[tuple[float, float, int, int, NormalizedTech]] = []

        for tech in technologies:
            if is_resource_like_repository(tech.name, tech.description):
                continue

            provisional = score_technology_breakdown(
                tech.signals,
                evidence=[],
                github_stars=float(tech.stars),
                github_forks=float(tech.forks),
            )
            editorially_plausible = is_trial_ring_editorially_eligible(
                tech.name,
                tech.description,
                getattr(tech, "topics", []),
            )
            has_package_mapping = bool(self._pypistats_subjects_for(tech) or self._deps_dev_subjects_for(tech))

            if not editorially_plausible and not has_package_mapping:
                continue
            if provisional.composite < min_score and tech.hn_mentions <= 0 and not has_package_mapping:
                continue

            ranked.append(
                (
                    provisional.composite,
                    provisional.mindshare,
                    int(tech.hn_mentions),
                    int(tech.stars),
                    tech,
                )
            )

        ranked.sort(reverse=True, key=lambda item: item[:4])
        return [tech for *_metrics, tech in ranked]

    def _safe_fetch_evidence(self, source: Any, subjects: List[str]) -> List[EvidenceRecord]:
        if not subjects:
            return []
        source_name = self._source_name_for(source)
        started = perf_counter()
        try:
            records = list(source.fetch(subjects))
            self.run_metrics.record_source(source_name, len(records), perf_counter() - started)
            return records
        except Exception as exc:
            self.run_metrics.record_source(source_name, 0, perf_counter() - started, failures=1)
            logger.warning("External evidence source %s failed for %s: %s", type(source).__name__, subjects, exc)
            return []

    def _source_name_for(self, source: Any) -> str:
        for name, registered in self.source_registry.as_dict().items():
            if registered is source:
                return name
        return type(source).__name__

    def _looks_like_package_name(self, name: str) -> bool:
        value = str(name or "").strip()
        normalized = self._normalize_id(value)
        blocked = {"python", "javascript", "java", "rust", "go", "php", "ruby", "c", "c++", "c#"}
        return bool(value) and " " not in value and normalized not in blocked

    def _deps_dev_subjects_for(self, tech: NormalizedTech) -> List[str]:
        ecosystem = self._infer_package_ecosystem(tech)
        subject = deps_dev_subject_for(tech.name, ecosystem=ecosystem)
        if subject is None:
            return []
        return [subject]

    def _pypistats_subjects_for(self, tech: NormalizedTech) -> List[str]:
        if self._infer_package_ecosystem(tech) != "pypi":
            return []
        subject = pypistats_subject_for(tech.name)
        if subject is None:
            return []
        return [subject]

    def _osv_subjects_for(self, tech: NormalizedTech) -> List[str]:
        subjects: List[str] = []
        for record in getattr(tech, "evidence", []) or []:
            if record.source == "deps_dev" and record.metric == "default_version":
                subjects.append(str(record.subject_id))
        return subjects

    def _infer_package_ecosystem(self, tech: NormalizedTech) -> Optional[str]:
        language = str(tech.language or "").strip().lower()
        if language == "python":
            return "pypi"
        if language in {"javascript", "typescript"}:
            return "npm"
        if language == "rust":
            return "cargo"
        if language == "go":
            return "go"
        return None

    def _apply_market_scoring(self, technologies: List[NormalizedTech]) -> List[NormalizedTech]:
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
            tech.signals["gh_popularity"] = scale_signal_logarithmically(float(tech.stars), 250000.0, 100.0)
            tech.signals.setdefault("hn_heat", min(100.0, float(tech.hn_mentions) * 10.0))
            tech.signals.setdefault("gh_momentum", tech.signals.get("gh_momentum", 0.0))

            signal_values = [
                float(tech.signals.get("gh_momentum", 0.0)),
                float(tech.signals.get("gh_popularity", 0.0)),
                float(tech.signals.get("hn_heat", 0.0)),
            ]
            variance = pvariance(signal_values) if len(signal_values) > 1 else 0.0
            score_summary = score_technology_breakdown(
                tech.signals,
                evidence=getattr(tech, "evidence", []),
                github_stars=float(tech.stars),
                github_forks=float(tech.forks),
            )
            tech.market_score = score_summary.composite
            tech.signals["adoption_score"] = score_summary.adoption
            tech.signals["mindshare_score"] = score_summary.mindshare
            tech.signals["health_score"] = score_summary.health
            tech.signals["risk_score"] = score_summary.risk
            tech.signals["source_coverage"] = float(score_summary.source_coverage)
            tech.signals["has_external_adoption"] = 1.0 if score_summary.has_external_adoption else 0.0
            tech.signals["github_only"] = 1.0 if score_summary.github_only else 0.0
            tech.signals["score_confidence"] = calculate_confidence(score_summary.source_coverage, variance)

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

        deterministic_techs: List[NormalizedTech] = []
        llm_candidates: List[NormalizedTech] = []
        for tech in borderline_techs:
            if self._should_use_deterministic_borderline_classification(tech):
                deterministic_techs.append(tech)
            else:
                llm_candidates.append(tech)

        if not llm_candidates:
            return self._fallback_classification(borderline_techs)

        # Respect budget - prioritize by uncertainty (lower confidence first)
        prioritized = sorted(llm_candidates, key=lambda t: t.signals.get("score_confidence", 0.5))
        to_classify = prioritized[:budget_remaining]

        if len(to_classify) < len(llm_candidates):
            logger.warning(f"Budget limited: classifying {len(to_classify)} of {len(llm_candidates)} "
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
            fallback_techs = deterministic_techs + [t for t in llm_candidates if t not in to_classify]
            if fallback_techs:
                fallback_classifications = self._fallback_classification(fallback_techs)
                # Merge results
                return llm_classifications + fallback_classifications

            return llm_classifications
        except Exception as e:
            logger.warning(f"AI classification failed: {e}, using fallback for borderline")
            return self._fallback_classification(borderline_techs)

    def _should_use_deterministic_borderline_classification(self, tech: NormalizedTech) -> bool:
        if is_resource_like_repository(tech.name, tech.description):
            return True
        if not is_trial_ring_editorially_eligible(tech.name, tech.description, getattr(tech, "topics", [])):
            return True

        signals = getattr(tech, "signals", {}) or {}
        source_coverage = int(round(float(signals.get("source_coverage", 0.0) or 0.0)))
        score_confidence = float(signals.get("score_confidence", 0.0) or 0.0)
        has_external_adoption = bool(float(signals.get("has_external_adoption", 0.0) or 0.0))

        return has_external_adoption and source_coverage >= 3 and score_confidence >= 0.7

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
            quadrant = self._infer_quadrant(tech)

            results.append(ClassificationResult(
                name=tech.name,
                quadrant=quadrant,
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

    def _get_deprecated_info(self, name: str) -> Optional[Dict[str, str]]:
        """Resolve deprecation metadata by tolerant name matching."""
        raw_name = str(name or "").strip().lower()
        if not raw_name:
            return None

        normalized_dash = re.sub(r"[^a-z0-9]+", "-", raw_name).strip("-")
        normalized_compact = re.sub(r"[^a-z0-9]+", "", raw_name)
        candidates = {
            raw_name,
            raw_name.replace("_", "-"),
            raw_name.replace(" ", "-"),
            normalized_dash,
            normalized_compact,
        }
        candidates = {candidate for candidate in candidates if candidate}

        for deprecated_name, info in DEPRECATED_MAP.items():
            key = str(deprecated_name or "").strip().lower()
            if not key:
                continue
            key_dash = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
            key_compact = re.sub(r"[^a-z0-9]+", "", key)
            if key in candidates or key_dash in candidates or key_compact in candidates:
                if isinstance(info, dict):
                    return info
                return {"replacement": "", "reason": str(info)}

        return None

    def _to_strategic_value(self, value: Any) -> StrategicValue:
        if isinstance(value, StrategicValue):
            return value
        normalized = str(value or "medium").lower().strip()
        if normalized == "high":
            return StrategicValue.HIGH
        if normalized == "low":
            return StrategicValue.LOW
        return StrategicValue.MEDIUM

    def _coerce_evidence_records(self, raw_records: Any) -> List[EvidenceRecord]:
        records: List[EvidenceRecord] = []
        for raw in raw_records if isinstance(raw_records, list) else []:
            if isinstance(raw, EvidenceRecord):
                records.append(raw)
                continue
            if not isinstance(raw, dict):
                continue
            try:
                records.append(
                    EvidenceRecord(
                        source=str(raw.get("source", "")),
                        metric=str(raw.get("metric", "")),
                        subject_id=str(raw.get("subjectId") or raw.get("subject_id") or ""),
                        raw_value=raw.get("rawValue", raw.get("raw_value", 0.0)),
                        normalized_value=float(raw.get("normalizedValue", raw.get("normalized_value", 0.0)) or 0.0),
                        observed_at=str(raw.get("observedAt", raw.get("observed_at", datetime.now().isoformat()))),
                        freshness_days=int(raw.get("freshnessDays", raw.get("freshness_days", 1)) or 1),
                    )
                )
            except Exception:
                continue
        return records

    def _signal_evidence_fallback(self, name: str, signals: Dict[str, Any]) -> List[EvidenceRecord]:
        if not isinstance(signals, dict):
            return []

        tech_id = self._normalize_id(name)
        observed_at = datetime.now().isoformat()
        synthetic: List[EvidenceRecord] = []

        def _append_if_positive(source: str, metric: str, signal_key: str, subject_prefix: str) -> None:
            try:
                value = float(signals.get(signal_key, 0.0) or 0.0)
            except Exception:
                value = 0.0
            if value <= 0.0:
                return
            synthetic.append(
                EvidenceRecord(
                    source=source,
                    metric=metric,
                    subject_id=f"{subject_prefix}:{tech_id}",
                    raw_value=round(value, 2),
                    normalized_value=max(0.0, min(100.0, round(value, 2))),
                    observed_at=observed_at,
                    freshness_days=1,
                )
            )

        _append_if_positive("github", "gh_momentum", "gh_momentum", "github")
        _append_if_positive("github", "gh_popularity", "gh_popularity", "github")
        _append_if_positive("hackernews", "hn_heat", "hn_heat", "hn")
        return synthetic

    def _build_filtered_item(
        self,
        tech: NormalizedTech,
        classification: ClassificationResult,
        confidence_floor: float = 0.5,
    ) -> FilteredItem:
        deprecated_info = self._get_deprecated_info(getattr(classification, "name", "") or tech.name)
        explicit_deprecated = bool(getattr(classification, "is_deprecated", False))
        replacement = getattr(classification, "replacement", None)
        if not replacement and deprecated_info:
            replacement = deprecated_info.get("replacement")
        item = FilteredItem(
            name=classification.name,
            description=classification.description,
            stars=tech.stars,
            quadrant=classification.quadrant,
            ring="trial",
            confidence=max(confidence_floor, classification.confidence),
            trend=classification.trend,
            strategic_value=self._to_strategic_value(getattr(classification, "strategic_value", "medium")),
            suspicion_flags=list(getattr(classification, "suspicion_flags", []) or []),
            is_deprecated=explicit_deprecated or deprecated_info is not None,
            replacement=replacement,
        )
        setattr(item, "market_score", tech.market_score)
        setattr(item, "signals", tech.signals)
        setattr(item, "moved", tech.moved)
        setattr(item, "sources", tech.sources)
        setattr(item, "topics", getattr(tech, "topics", []))
        setattr(item, "canonical_id", getattr(classification, "canonical_id", None) or getattr(tech, "canonical_id", None))
        setattr(item, "entity_type", getattr(classification, "entity_type", None) or getattr(tech, "entity_type", "technology"))
        signals = getattr(tech, "signals", {}) if isinstance(getattr(tech, "signals", {}), dict) else {}
        evidence = list(getattr(classification, "evidence", None) or getattr(tech, "evidence", []) or [])
        if not evidence:
            evidence = self._signal_evidence_fallback(classification.name, signals)
        setattr(
            item,
            "evidence",
            evidence,
        )
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
        for item in items:
            tech_id = item.name.lower().replace(" ", "-")
            previous_entry = previous_map.get(tech_id)
            prev_ring = previous_entry.get("ring") if isinstance(previous_entry, dict) else None
            market_score = float(getattr(item, "market_score", 0.0))
            trend_delta = 0.0
            if previous_entry is not None:
                previous_market_score = float(previous_entry.get("marketScore", 0.0))
                trend_delta = market_score - previous_market_score

            signals = getattr(item, "signals", {}) or {}
            trial_editorial_exception = is_trial_ring_editorially_eligible(
                item.name,
                item.description,
                getattr(item, "topics", []),
            )
            deprecated_info = self._get_deprecated_info(getattr(item, "name", ""))
            if deprecated_info is not None:
                setattr(item, "is_deprecated", True)
                replacement = getattr(item, "replacement", None)
                if not replacement:
                    setattr(item, "replacement", deprecated_info.get("replacement"))
            if bool(getattr(item, "is_deprecated", False)):
                ring = "hold"
                item.ring = ring
                setattr(item, "moved", 0)
                if isinstance(prev_ring, str) and prev_ring in RING_INDEX and ring in RING_INDEX:
                    setattr(item, "moved", RING_INDEX[ring] - RING_INDEX[prev_ring])
                item.trend = "down"
                continue
            ring = decide_ring(
                {
                    "adoption": float(signals.get("adoption_score", 0.0) or 0.0),
                    "mindshare": float(signals.get("mindshare_score", 0.0) or 0.0),
                    "health": float(signals.get("health_score", 0.0) or 0.0),
                    "risk": float(signals.get("risk_score", 0.0) or 0.0),
                    "composite": market_score,
                },
                source_coverage=max(1, int(round(float(signals.get("source_coverage", 1.0) or 1.0)))),
                has_external_adoption=bool(float(signals.get("has_external_adoption", 0.0) or 0.0)),
                github_only=bool(float(signals.get("github_only", 0.0) or 0.0)),
                editorial_exception=trial_editorial_exception,
                previous_ring=prev_ring if isinstance(prev_ring, str) else None,
                thresholds=thresholds,
                hysteresis=hysteresis,
            )

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

        def _collect_source_names(raw_signals: Dict[str, Any], evidence: List[EvidenceRecord]) -> List[str]:
            sources: List[str] = []
            if float(raw_signals.get("gh_momentum", 0.0) or 0.0) > 0.0 or float(raw_signals.get("gh_popularity", 0.0) or 0.0) > 0.0:
                sources.append("github")
            if float(raw_signals.get("hn_heat", 0.0) or 0.0) > 0.0:
                sources.append("hackernews")
            for record in evidence:
                source = str(record.source or "").strip().lower()
                if source and source not in sources:
                    sources.append(source)
            return sources

        def _source_coverage(raw_signals: Dict[str, Any], evidence: List[EvidenceRecord]) -> int:
            explicit = int(round(float(raw_signals.get("source_coverage", 0.0) or 0.0)))
            if explicit > 0:
                return explicit
            return len(_collect_source_names(raw_signals, evidence))

        def _evidence_summary(raw_signals: Dict[str, Any], evidence: List[EvidenceRecord]) -> Dict[str, Any]:
            adoption_metrics = {"reverse_dependents", "downloads_last_month"}
            source_names = _collect_source_names(raw_signals, evidence)
            metrics = sorted({str(record.metric) for record in evidence if getattr(record, "metric", None)})
            has_external_adoption = bool(float(raw_signals.get("has_external_adoption", 0.0) or 0.0)) or any(
                str(record.metric).strip().lower() in adoption_metrics
                and str(record.source).strip().lower() not in {"github", "hackernews"}
                for record in evidence
            )
            github_only = source_names == ["github"]
            return {
                "sources": source_names,
                "metrics": metrics,
                "hasExternalAdoption": has_external_adoption,
                "githubOnly": github_only,
            }

        def _source_freshness(raw_signals: Dict[str, Any], evidence: List[EvidenceRecord]) -> Dict[str, Any]:
            freshness_days = [int(record.freshness_days) for record in evidence if getattr(record, "freshness_days", None) is not None]
            if not freshness_days:
                return {"freshestDays": None, "stalestDays": None}
            return {
                "freshestDays": min(freshness_days),
                "stalestDays": max(freshness_days),
            }

        def _normalize_editorial_flag(flag: Any) -> str:
            normalized = str(flag or "").strip()
            if not normalized:
                return ""
            parts = [part for part in re.split(r"[^a-zA-Z0-9]+", normalized) if part]
            if not parts:
                return ""
            first = parts[0].lower()
            rest = [part[:1].upper() + part[1:].lower() for part in parts[1:]]
            normalized_flag = f"{first}{''.join(rest)}"
            if normalized_flag == "missingevidence":
                return "missingEvidence"
            return normalized_flag

        def _append_unique_flags(flags: List[str], extra_flags: List[Any]) -> None:
            for raw_flag in extra_flags:
                flag = _normalize_editorial_flag(raw_flag)
                if flag and flag not in flags:
                    flags.append(flag)

        def _editorial_status(
            raw_signals: Dict[str, Any],
            evidence: List[EvidenceRecord],
            suspicion_flags: List[Any],
        ) -> tuple[str, List[str]]:
            flags: List[str] = []
            _append_unique_flags(flags, suspicion_flags)
            source_coverage = _source_coverage(raw_signals, evidence)
            if source_coverage > 0 and not evidence:
                _append_unique_flags(flags, ["missingEvidence"])
            status = "invalid" if flags else "clean"
            return status, flags

        def _why_this_ring(
            ring: str,
            market_score: float,
            raw_signals: Dict[str, Any],
            evidence_summary: Dict[str, Any],
            source_coverage: int,
            editorial_status: str,
            editorial_flags: List[str],
        ) -> str:
            if editorial_status == "invalid" and "missingEvidence" in editorial_flags:
                return (
                    f"{ring.capitalize()} candidate scored {market_score:.1f}, but publication is blocked "
                    f"because source coverage is claimed across {source_coverage} sources without atomic evidence."
                )
            reason = "corroborated signals"
            if evidence_summary.get("hasExternalAdoption"):
                reason = "external adoption evidence"
            elif evidence_summary.get("githubOnly"):
                reason = "limited GitHub-first evidence"
            if ring == "adopt":
                return f"Adopt because composite {market_score:.1f} is backed by {reason} across {source_coverage} sources."
            if ring == "trial":
                return f"Trial because composite {market_score:.1f} shows momentum with {reason} across {source_coverage} sources."
            if ring == "assess":
                return f"Assess because composite {market_score:.1f} is promising but evidence depth is still limited."
            return f"Hold because composite {market_score:.1f} lacks enough corroborated evidence for stronger rings."

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
                evidence = list(getattr(item, "evidence", []) or [])
                suspicion_flags = list(getattr(item, "suspicion_flags", []) or [])
                source_coverage = _source_coverage(raw_signals, evidence)
                evidence_summary = _evidence_summary(raw_signals, evidence)
                source_freshness = _source_freshness(raw_signals, evidence)
                editorial_status, editorial_flags = _editorial_status(raw_signals, evidence, suspicion_flags)
                market_score = round(float(getattr(item, 'market_score', 0.0)), 2)

                payload.append({
                    'id': self._normalize_id(item.name),
                    'name': item.name,
                    'quadrant': item.quadrant,
                    'ring': item.ring,
                    'description': description,
                    'moved': int(getattr(item, 'moved', 0)),
                    'trend': item.trend,
                    'marketScore': market_score,
                    'signals': signals,
                    'sourceCoverage': source_coverage,
                    'sourceFreshness': source_freshness,
                    'evidenceSummary': evidence_summary,
                    'whyThisRing': _why_this_ring(
                        item.ring,
                        market_score,
                        raw_signals,
                        evidence_summary,
                        source_coverage,
                        editorial_status,
                        editorial_flags,
                    ),
                    'editorialStatus': editorial_status,
                    'editorialFlags': editorial_flags,
                    'stars': item.stars,
                    'confidence': item.confidence,
                    'isDeprecated': bool(getattr(item, 'is_deprecated', False)),
                    'replacement': getattr(item, 'replacement', None),
                    'updatedAt': datetime.now().isoformat()
                })

                serialized = payload[-1]
                canonical_id = getattr(item, "canonical_id", None)
                if canonical_id:
                    serialized["canonicalId"] = str(canonical_id)

                entity_type = getattr(item, "entity_type", None)
                if entity_type:
                    serialized["entityType"] = str(entity_type)

                if evidence:
                    serialized["evidence"] = [
                        {
                            "source": str(record.source),
                            "metric": str(record.metric),
                            "subjectId": str(record.subject_id),
                            "rawValue": record.raw_value,
                            "normalizedValue": float(record.normalized_value),
                            "observedAt": str(record.observed_at),
                            "freshnessDays": int(record.freshness_days),
                        }
                        for record in evidence
                    ]

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
        ring_fill_status, underfilled_rings = self._soft_ring_fill_status(ring_distribution)

        quality = build_artifact_quality(technologies)

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
                    'runMetrics': self.run_metrics.to_dict(),
                    'ringDistribution': ring_distribution,
                    'ringFillStatus': ring_fill_status,
                    'underfilledRings': underfilled_rings,
                    'ringQuality': quality["ringQuality"],
                    'quadrantQuality': quality["quadrantQuality"],
                    'quadrantRingQuality': quality["quadrantRingQuality"],
                    'topAdded': top_added,
                    'topDropped': top_dropped,
                }
            }
        }

    def _is_low_quality_assess_item(self, item: FilteredItem) -> bool:
        if str(getattr(item, "ring", "")) != "assess":
            return False

        raw_signals = getattr(item, "signals", {}) or {}
        if not isinstance(raw_signals, dict):
            raw_signals = {}

        gh_momentum = float(raw_signals.get("gh_momentum", 0.0) or 0.0)
        gh_popularity = float(raw_signals.get("gh_popularity", 0.0) or 0.0)
        hn_heat = float(raw_signals.get("hn_heat", 0.0) or 0.0)
        source_coverage = float(raw_signals.get("source_coverage", 0.0) or 0.0)
        has_external_adoption = bool(float(raw_signals.get("has_external_adoption", 0.0) or 0.0))

        github_only_raw = raw_signals.get("github_only")
        if github_only_raw is None:
            github_only = (gh_momentum > 0.0 or gh_popularity > 0.0) and hn_heat <= 0.0
        else:
            github_only = bool(float(github_only_raw or 0.0))
        if source_coverage > 0.0 and source_coverage <= 1.0 and (gh_momentum > 0.0 or gh_popularity > 0.0) and not has_external_adoption:
            github_only = True

        editorially_plausible = is_trial_ring_editorially_eligible(
            str(getattr(item, "name", "")),
            str(getattr(item, "description", "")),
            getattr(item, "topics", []),
        )
        market_score = float(getattr(item, "market_score", 0.0) or 0.0)

        return github_only and not has_external_adoption and hn_heat <= 0.0 and (
            market_score < 60.0 or not editorially_plausible
        )

    def _is_reasonable_watchlist_item(self, item: FilteredItem) -> bool:
        if not self._is_editorially_valid_for_selection(item):
            return False

        name = str(getattr(item, "name", ""))
        description = str(getattr(item, "description", ""))
        if is_resource_like_repository(name, description):
            return False
        combined_text = f"{name} {description}".lower()
        if any(token in combined_text for token in ("100-days", "curriculum", "bootcamp")):
            return False

        raw_signals = getattr(item, "signals", {}) or {}
        if not isinstance(raw_signals, dict):
            raw_signals = {}

        source_coverage = float(raw_signals.get("source_coverage", 0.0) or 0.0)
        has_external_adoption = bool(float(raw_signals.get("has_external_adoption", 0.0) or 0.0))
        hn_heat = float(raw_signals.get("hn_heat", 0.0) or 0.0)
        market_score = float(getattr(item, "market_score", 0.0) or 0.0)
        ring = str(getattr(item, "ring", "")).strip().lower()

        if ring == "hold":
            return has_external_adoption or hn_heat > 0.0 or market_score >= 55.0

        if ring == "assess":
            return has_external_adoption or hn_heat > 0.0 or (source_coverage >= 1.0 and market_score >= 57.0)

        return market_score >= 50.0

    def _is_editorially_valid_for_selection(self, item: FilteredItem) -> bool:
        editorial_status = str(getattr(item, "editorial_status", "") or getattr(item, "editorialStatus", "")).strip().lower()
        if editorial_status == "invalid":
            return False

        raw_signals = getattr(item, "signals", {}) or {}
        if not isinstance(raw_signals, dict):
            raw_signals = {}

        source_coverage_raw = raw_signals.get("source_coverage")
        if source_coverage_raw is None:
            gh_momentum = float(raw_signals.get("gh_momentum", 0.0) or 0.0)
            gh_popularity = float(raw_signals.get("gh_popularity", 0.0) or 0.0)
            hn_heat = float(raw_signals.get("hn_heat", 0.0) or 0.0)
            source_coverage = int((gh_momentum > 0.0 or gh_popularity > 0.0) + (hn_heat > 0.0))
        else:
            source_coverage = int(round(float(source_coverage_raw or 0.0)))
        evidence = list(getattr(item, "evidence", []) or [])
        if source_coverage > 0 and not evidence:
            return False

        if not evidence and source_coverage <= 0:
            return True

        normalized_flags = {
            "".join(ch for ch in str(flag or "").strip().lower() if ch.isalnum())
            for flag in (list(getattr(item, "suspicion_flags", []) or []) + list(getattr(item, "editorialFlags", []) or []))
            if str(flag or "").strip()
        }
        return not normalized_flags

    def _soft_ring_fill_status(self, ring_distribution: Dict[str, int]) -> tuple[Dict[str, Dict[str, Any]], List[str]]:
        target_per_ring = max(0, int(getattr(self.config.distribution, "target_per_ring", 0) or 0))
        max_per_ring = max(target_per_ring, int(getattr(self.config.distribution, "max_per_ring", target_per_ring) or 0))
        ring_order = ("adopt", "trial", "assess", "hold")
        ring_fill_status: Dict[str, Dict[str, Any]] = {}
        underfilled_rings: List[str] = []

        for ring in ring_order:
            actual = int(ring_distribution.get(ring, 0))
            underfilled = target_per_ring > 0 and actual < target_per_ring
            ring_fill_status[ring] = {
                "actual": actual,
                "target": target_per_ring,
                "max": max_per_ring,
                "underfilled": underfilled,
            }
            if underfilled:
                underfilled_rings.append(ring)

        return ring_fill_status, underfilled_rings

    def _ensure_ring_presence(self, items: List[FilteredItem]) -> List[FilteredItem]:
        def _item_market_score(item: FilteredItem) -> float:
            explicit = float(getattr(item, "market_score", 0.0) or 0.0)
            if explicit > 0.0:
                return explicit

            raw_signals = getattr(item, "signals", {}) or {}
            if not isinstance(raw_signals, dict):
                return 0.0

            adoption = float(raw_signals.get("adoption_score", 0.0) or 0.0)
            mindshare = float(raw_signals.get("mindshare_score", 0.0) or 0.0)
            health = float(raw_signals.get("health_score", 0.0) or 0.0)
            risk = float(raw_signals.get("risk_score", 0.0) or 0.0)
            weighted = (adoption * 0.45) + (mindshare * 0.20) + (health * 0.20) + (risk * 0.15)
            if weighted > 0.0:
                return weighted

            gh_momentum = float(raw_signals.get("gh_momentum", 0.0) or 0.0)
            gh_popularity = float(raw_signals.get("gh_popularity", 0.0) or 0.0)
            hn_heat = float(raw_signals.get("hn_heat", 0.0) or 0.0)
            return (gh_momentum * 0.4) + (gh_popularity * 0.4) + (hn_heat * 0.2)

        ring_counts = {"adopt": 0, "trial": 0, "assess": 0, "hold": 0}
        for item in items:
            ring = str(getattr(item, "ring", "")).strip().lower()
            if ring in ring_counts:
                ring_counts[ring] += 1

        if ring_counts["assess"] > 0:
            return items

        candidates: List[FilteredItem] = []
        for item in items:
            if str(getattr(item, "ring", "")).strip().lower() != "trial":
                continue
            raw_signals = getattr(item, "signals", {}) or {}
            if not isinstance(raw_signals, dict):
                raw_signals = {}
            source_coverage = float(raw_signals.get("source_coverage", 0.0) or 0.0)
            has_external = bool(float(raw_signals.get("has_external_adoption", 0.0) or 0.0))
            if source_coverage >= 2.0 or has_external:
                candidates.append(item)

        if not candidates:
            return items

        demoted = min(candidates, key=_item_market_score)
        demoted.ring = "assess"
        logger.info(
            "Phase 5d - Demoted %s to assess to preserve ring coverage with quality evidence",
            demoted.name,
        )
        return items

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

        technologies = self._attach_external_evidence(technologies)
        logger.info("Phase 3a - External evidence attachment complete")
        self._save_checkpoint("external_evidence")

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
        reserve_candidates = self._assign_market_rings(list(getattr(self, "_last_selection_candidates", []) or []))
        filtered_items = rebalance_soft_ring_targets(
            self,
            filtered_items,
            reserve_candidates,
            RADAR_QUADRANTS,
        )
        removed_low_quality_main = len(filtered_items)
        filtered_items = [item for item in filtered_items if not self._is_low_quality_assess_item(item)]
        removed_low_quality_main -= len(filtered_items)
        if removed_low_quality_main > 0:
            logger.info(
                "Phase 5b - Removed %s low-quality assess items from main radar",
                removed_low_quality_main,
            )
        filtered_items = self._ensure_ring_presence(filtered_items)

        watchlist_items = self._build_watchlist_items(
            technologies,
            classifications,
            candidate_selection,
            main_ids={self._normalize_id(item.name) for item in filtered_items},
        )
        watchlist_items = self._assign_market_rings(watchlist_items)
        for item in watchlist_items:
            if str(getattr(item, "ring", "")) == "adopt":
                item.ring = "trial"
        removed_low_quality_watchlist = [
            item for item in watchlist_items if self._is_low_quality_assess_item(item)
        ]
        watchlist_items = [item for item in watchlist_items if not self._is_low_quality_assess_item(item)]
        if removed_low_quality_watchlist:
            logger.info(
                "Phase 5c - Removed %s low-quality assess items from watchlist",
                len(removed_low_quality_watchlist),
            )
        if not watchlist_items and removed_low_quality_watchlist:
            rescued_items = [
                item for item in removed_low_quality_watchlist
                if self._is_reasonable_watchlist_item(item)
            ]
            rescued_items.sort(
                key=lambda item: float(getattr(item, "market_score", 0.0) or 0.0),
                reverse=True,
            )
            if rescued_items:
                watchlist_items = rescued_items[:2]
                logger.info(
                    "Phase 5c - Rescued %s reasonable items into watchlist to avoid empty output",
                    len(watchlist_items),
                )

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
