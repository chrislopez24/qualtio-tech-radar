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
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass

from etl.config import ETLConfig, SourcesConfig, ClassificationConfig, FilteringConfig, DeepScanConfig
from etl.ai_filter import AITechnologyFilter, FilteredItem, StrategicValue
from etl.deep_scanner import DeepScanner
from scraper.github_scraper import GitHubScraper
from scraper.hackernews import HackerNewsScraper
from ai.classifier import TechnologyClassifier, ClassificationResult

logger = logging.getLogger(__name__)


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
    sources: List[str] = None

    def __post_init__(self):
        if self.sources is None:
            self.sources = []


class RadarPipeline:
    """Main pipeline orchestrator for Tech Radar ETL"""

    def __init__(self, config: Optional[ETLConfig] = None):
        self.config = config or ETLConfig()
        self._init_components()

    def _init_components(self):
        """Initialize pipeline components"""
        self.github_scraper = GitHubScraper()
        self.hn_scraper = HackerNewsScraper()

        if self.config.classification:
            try:
                self.classifier = TechnologyClassifier()
            except ValueError:
                logger.warning("AI classifier not available, using fallback")
                self.classifier = None
        else:
            self.classifier = None

        self.filter = AITechnologyFilter(self.config.filtering)

        self.deep_scanner = DeepScanner(
            allowed_repos=self.config.deep_scan.repos if self.config.deep_scan else None,
            use_ai_analysis=False
        )

    def _collect_sources(self) -> List[NormalizedTech]:
        """Phase 1: Collect signals from all sources"""
        technologies: Dict[str, NormalizedTech] = {}

        if self.config.sources.github_trending.enabled:
            repos = self.github_scraper.get_trending_repos(
                min_stars=100,
                limit=50
            )
            for repo in repos:
                technologies[repo.name] = NormalizedTech(
                    name=repo.name,
                    description=repo.description,
                    stars=repo.stars,
                    forks=repo.forks,
                    language=repo.language,
                    topics=repo.topics,
                    url=repo.url,
                    sources=["github"]
                )

        if self.config.sources.hackernews.enabled:
            hn_posts = self.hn_scraper.search_tech_posts(
                min_points=self.config.sources.hackernews.min_points,
                limit=50
            )
            for post in hn_posts:
                tech_name = self._extract_tech_name(post.title)
                if tech_name:
                    if tech_name in technologies:
                        technologies[tech_name].hn_mentions += 1
                        technologies[tech_name].sources.append("hackernews")
                    else:
                        technologies[tech_name] = NormalizedTech(
                            name=tech_name,
                            description=post.title,
                            stars=0,
                            forks=0,
                            language=None,
                            topics=[],
                            url=post.url,
                            hn_mentions=1,
                            sources=["hackernews"]
                        )

        return list(technologies.values())

    def _extract_tech_name(self, title: str) -> Optional[str]:
        """Extract technology name from HN post title"""
        title_lower = title.lower()
        words = title_lower.split()
        for word in words:
            if len(word) > 3 and word not in ["this", "that", "with", "from", "new", "use", "using"]:
                return word
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
            if not hasattr(tech, 'last_updated'):
                tech.last_updated = now
            if not hasattr(tech, 'domain'):
                tech.domain = self._infer_domain(tech)
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
        """Phase 5: Strategic filtering"""
        items = []
        for tech, classification in zip(technologies, classifications):
            items.append(type('TechItem', (), {
                'name': classification.name,
                'description': classification.description,
                'stars': tech.stars,
                'quadrant': classification.quadrant,
                'ring': classification.ring,
                'confidence': classification.confidence,
                'trend': classification.trend
            })())

        return self.filter.filter(items)

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
        for item in items:
            technologies.append({
                'id': item.name.lower().replace(' ', '-'),
                'name': item.name,
                'quadrant': item.quadrant,
                'ring': item.ring,
                'description': item.description,
                'moved': 0,
                'trend': item.trend,
                'stars': item.stars,
                'confidence': item.confidence,
                'isDeprecated': item.is_deprecated,
                'replacement': item.replacement,
                'updatedAt': datetime.now().isoformat()
            })

        return {
            'updatedAt': datetime.now().isoformat(),
            'technologies': technologies
        }

    def run(self) -> Dict[str, Any]:
        """Run the complete pipeline"""
        logger.info("Starting Tech Radar Pipeline")

        technologies = self._collect_sources()
        logger.info(f"Phase 1 - Collected {len(technologies)} technologies from sources")

        technologies = self._normalize_and_dedupe(technologies)
        logger.info(f"Phase 2 - Normalized and deduplicated to {len(technologies)} technologies")

        technologies = self._temporal_enrichment(technologies)
        logger.info("Phase 3 - Temporal/domain enrichment complete")

        classifications = self._classify_ai(technologies)
        logger.info(f"Phase 4 - AI classification complete for {len(classifications)} items")

        filtered_items = self._strategic_filter(technologies, classifications)
        logger.info(f"Phase 5 - Strategic filtering complete, {len(filtered_items or [])} items remain")

        enriched_items = self._deep_scan_enrich(filtered_items)
        logger.info(f"Phase 6 - Deep scan enrichment complete")

        output = self._generate_output(enriched_items or [])
        logger.info(f"Phase 7 - Output generated with {len(output['technologies'])} technologies")

        return output


def run(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Run pipeline with optional config path"""
    if config_path:
        config = load_etl_config(config_path)
    else:
        config = ETLConfig()

    pipeline = RadarPipeline(config)
    return pipeline.run()


def load_etl_config(config_path: str) -> ETLConfig:
    """Load ETL config from path"""
    from etl.config import load_etl_config as load_config
    return load_config(config_path)