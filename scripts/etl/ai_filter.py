"""AI-powered strategic filter for technology radar items

This module provides strategic value filtering to reduce noise in the radar
by filtering out low-value items like utility libraries.
"""

import os
import json
import numbers
import logging
import re
from enum import Enum
from typing import List, Optional, Any, Protocol
from dataclasses import dataclass

from openai import OpenAI

logger = logging.getLogger(__name__)


class StrategicValue(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


DEFAULT_AUTO_IGNORE = [
    "rimraf",
    "chalk",
    "ansi-styles",
    "debug",
    "is-odd",
    "is-even",
    "left-pad",
    "right-pad",
    "tiny-invariant",
    "clsx",
    "cond",
    "wrapt",
    "prettier",
    "eslint",
    "prettierrc",
    "ts-node",
    "@types/node",
    "@types/react",
    "@types/lodash",
    "lodash",
    "underscore",
    "moment",
]

DUPLICATE_MERGE_GROUPS = {
    "eslint": ["ESLint", "eslint", "ESLint-config", "@eslint/js"],
    "prettier": ["Prettier", "prettier", "prettierrc"],
    "tslint": ["TSLint", "tslint"],
    "redux": ["Redux", "redux", "@reduxjs/toolkit"],
    "jest": ["Jest", "jest", "jest-runner"],
    "mocha": ["Mocha", "mocha"],
    "cypress": ["Cypress", "cypress"],
    "storybook": ["Storybook", "storybook"],
}

CANONICAL_DISPLAY_NAMES = {
    "eslint": "ESLint",
    "prettier": "Prettier",
    "tslint": "TSLint",
    "redux": "Redux",
    "jest": "Jest",
    "mocha": "Mocha",
    "cypress": "Cypress",
    "storybook": "Storybook",
}

PARENT_CHILD_HIERARCHY = {
    "firebase": ["@firebase/firestore", "@firebase/auth", "@firebase/database", "@firebase/functions", "@firebase/storage"],
    "aws-sdk": ["@aws-sdk/client-s3", "@aws-sdk/client-ec2", "@aws-sdk/lib-dynamodb"],
    "angular": ["@angular/core", "@angular/common", "@angular/compiler", "@angular/platform-browser"],
    "react": ["react-dom", "react-native", "react-router", "@types/react", "@types/react-dom"],
    "vue": ["vue-router", "vuex", "@vue/core", "@vue/reactivity"],
    "node": ["@types/node"],
}

DEPRECATED_MAP = {
    "tslint": {"replacement": "ESLint", "reason": "TSLint is deprecated in favor of ESLint with TypeScript support"},
    "moment.js": {"replacement": "date-fns or dayjs", "reason": "Moment.js is in maintenance mode"},
    "moment": {"replacement": "date-fns or dayjs", "reason": "Moment.js is in maintenance mode"},
    "request": {"replacement": "axios or fetch", "reason": "Request is deprecated"},
    "node-uuid": {"replacement": "uuid", "reason": "node-uuid is deprecated"},
    "joi": {"replacement": "zod or yup", "reason": "Joi is in maintenance mode"},
    "lodash": {"replacement": "native JS or date-fns", "reason": "Consider native alternatives for tree-shaking"},
    "underscore": {"replacement": "lodash or native JS", "reason": "Underscore is largely superseded by lodash"},
    "graphql": {"replacement": "@graphql-tools or nexus", "reason": "GraphQL ecosystem has evolved"},
}

RESOURCE_LIKE_EXACT_NAMES = {
    "awesome",
    "awesome-python",
    "build-your-own-x",
    "developer-roadmap",
    "free-programming-books",
    "gitignore",
    "public-apis",
    "system-prompts-and-models-of-ai-tools",
}

RESOURCE_LIKE_PREFIXES = (
    "awesome-",
    "build-your-own-",
)

RESOURCE_LIKE_PHRASES = (
    "curated list",
    "list of",
    "learning resources",
    "programming books",
    "free programming books",
    "roadmap",
    "roadmaps",
    "tutorial",
    "tutorials",
    "system prompts",
    "prompt collection",
    "prompt library",
)


def is_resource_like_repository(name: str, description: str = "") -> bool:
    """Detect repositories that are primarily educational/resource collections."""
    name_lower = str(name or "").strip().lower()
    description_lower = str(description or "").strip().lower()
    combined_text = f"{name_lower} {description_lower}".strip()

    if not combined_text:
        return False

    if name_lower in RESOURCE_LIKE_EXACT_NAMES:
        return True

    if any(name_lower.startswith(prefix) for prefix in RESOURCE_LIKE_PREFIXES):
        return True

    if re.search(r"\b(books|roadmap|roadmaps|tutorial|tutorials)\b", name_lower):
        return True

    phrase_matches = sum(1 for phrase in RESOURCE_LIKE_PHRASES if phrase in combined_text)
    if phrase_matches >= 2:
        return True

    return False


class FilterConfig(Protocol):
    auto_ignore: List[str]
    include_only: List[str]
    min_confidence: float


@dataclass
class FilteredItem:
    name: str
    description: str
    stars: int
    quadrant: str
    ring: str
    confidence: float
    trend: str
    strategic_value: StrategicValue
    is_deprecated: bool = False
    replacement: Optional[str] = None
    merged_names: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.merged_names is None:
            self.merged_names = []


class AITechnologyFilter:
    """AI-powered filter for technology radar items based on strategic value"""

    MODEL_TIMEOUTS = {
        "hf:minimaxai/minimax-m2.5": 60,
        "hf:moonshotai/kimi-k2.5": 120,
    }

    SYSTEM_PROMPT = """You are a technology analyst evaluating open-source projects for a tech radar.

Context:
- Tech radar tracks interesting technologies worth monitoring
- We want technologies with real adoption (GitHub stars), not just hype
- Focus on developer tools, frameworks, languages, and platforms

Evaluation Criteria:
1. ADOPTION: Does it have significant GitHub stars (>1000)? Active community?
2. UTILITY: Is it a broadly useful technology, not just a utility library?
3. MATURITY: Is it past early experimental phase?
4. RELEVANCE: Would developers care about this technology?

Categorization:
- HIGH: Major frameworks, languages, platforms (React, Kubernetes, PostgreSQL, etc.)
- MEDIUM: Solid tools with real adoption (testing frameworks, dev tools, libraries with >5000 stars)
- LOW: Tiny utilities, personal projects, abandoned repos, highly niche tools

Balanced approach: If a technology has >5000 GitHub stars and active development, it deserves MEDIUM or HIGH.

Respond with JSON only: {"strategic_value": "high|medium|low", "reason": "brief explanation"}"""

    PROMPT_VERSION = "v1"

    def __init__(self, config: FilterConfig, model: Optional[str] = None, llm_cache=None, max_drift: float = 3.0):
        self.config = config
        self.auto_ignore = set(config.auto_ignore) if config.auto_ignore is not None else set(DEFAULT_AUTO_IGNORE)
        self.include_only = set(config.include_only) if config.include_only else None
        self.min_confidence = config.min_confidence
        self.model = model or os.environ.get("SYNTHETIC_MODEL", "hf:MiniMaxAI/MiniMax-M2.5")
        self.timeout = self._resolve_timeout(30)
        self.llm_cache = llm_cache
        self.max_drift = max_drift

        self._client: Optional[OpenAI] = None
        if os.environ.get("SYNTHETIC_API_KEY"):
            self._client = OpenAI(
                api_key=os.environ.get("SYNTHETIC_API_KEY"),
                base_url=os.environ.get("SYNTHETIC_API_URL", "https://api.synthetic.new/v1"),
                timeout=self.timeout,
            )

        self.metrics = {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "small_requests": 0,
            "tool_calls": 0,
        }

    def _resolve_timeout(self, default_timeout: int) -> int:
        model_key = (self.model or "").lower()
        for prefix, timeout in self.MODEL_TIMEOUTS.items():
            if model_key.startswith(prefix):
                return timeout
        return default_timeout

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)

    def _normalize_token_value(self, value: Any, fallback: int) -> int:
        if isinstance(value, numbers.Integral):
            return int(value)
        return fallback

    def _log_request_metrics(self, name: str, prompt: str, response: Any, content: str) -> None:
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

        prompt_fallback = self._estimate_tokens(self.SYSTEM_PROMPT) + self._estimate_tokens(prompt)
        completion_fallback = self._estimate_tokens(content)

        prompt_tokens = self._normalize_token_value(prompt_tokens, prompt_fallback)
        completion_tokens = self._normalize_token_value(completion_tokens, completion_fallback)
        total_tokens = self._normalize_token_value(total_tokens, prompt_tokens + completion_tokens)

        choice = response.choices[0]
        message = choice.message
        raw_tool_calls = getattr(message, "tool_calls", None)
        if isinstance(raw_tool_calls, list):
            tool_calls = len(raw_tool_calls)
        elif raw_tool_calls is None:
            tool_calls = 0
        else:
            try:
                tool_calls = len(raw_tool_calls)
            except TypeError:
                tool_calls = 0
        finish_reason = getattr(choice, "finish_reason", None)
        small_request = prompt_tokens <= 2048 and completion_tokens <= 2048

        self.metrics["calls"] += 1
        self.metrics["prompt_tokens"] += int(prompt_tokens)
        self.metrics["completion_tokens"] += int(completion_tokens)
        self.metrics["total_tokens"] += int(total_tokens)
        self.metrics["tool_calls"] += tool_calls
        if small_request:
            self.metrics["small_requests"] += 1

        logger.info(
            "LLM filter request metrics | name=%s model=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s prompt_chars=%s completion_chars=%s tool_calls=%s finish_reason=%s small_request=%s",
            name,
            self.model,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            len(self.SYSTEM_PROMPT) + len(prompt),
            len(content),
            tool_calls,
            finish_reason,
            small_request,
        )

    def _evaluate_strategic_value(self, name: str, stars: int, description: str) -> StrategicValue:
        """Evaluate strategic value using AI or heuristics"""
        if self._client:
            try:
                return self._ai_evaluate(name, stars, description)
            except Exception as e:
                logger.warning(f"AI evaluation failed for {name}, falling back to heuristic: {e}")

        return self._heuristic_evaluate(name, stars, description)

    def _ai_evaluate(self, name: str, stars: int, description: str) -> StrategicValue:
        """Use AI to evaluate strategic value with caching"""
        if self._client is None:
            return self._heuristic_evaluate(name, stars, description)

        # Build features for cache key
        features = {
            "stars": float(stars),
        }

        # Check cache first (cache errors should not block pipeline)
        cached_value = None
        if self.llm_cache is not None:
            try:
                cached_value = self.llm_cache.get_if_fresh(
                    name=name,
                    model=self.model,
                    prompt_version=self.PROMPT_VERSION,
                    features=features,
                    max_drift=self.max_drift,
                )
            except Exception as e:
                logger.warning(f"Cache lookup failed for {name}: {e}")

        if cached_value is not None:
            logger.debug(f"Cache hit for {name}: {cached_value}")
            strategic_value = cached_value.get("strategic_value", "medium").lower()
            if strategic_value == "high":
                return StrategicValue.HIGH
            elif strategic_value == "low":
                return StrategicValue.LOW
            return StrategicValue.MEDIUM

        prompt = f"""Evaluate this technology:

Name: {name}
Description: {description}
GitHub Stars: {stars}

Consider the strategic value for a tech radar."""

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=8000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            self._log_request_metrics(name, prompt, response, "")
            return self._heuristic_evaluate(name, stars, description)

        self._log_request_metrics(name, prompt, response, content)

        json_str = content.strip()
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            json_str = "\n".join(lines).strip()

        try:
            data = json.loads(json_str)
            value = data.get("strategic_value", "medium").lower()
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON for {name}: {e}")
            return self._heuristic_evaluate(name, stars, description)

        # Store result in cache (cache errors should not block pipeline)
        if self.llm_cache is not None:
            try:
                cache_key = self.llm_cache.make_key(
                    name=name,
                    model=self.model,
                    prompt_version=self.PROMPT_VERSION,
                    features=features,
                )
                self.llm_cache.put(cache_key, data)
            except Exception as e:
                logger.warning(f"Cache store failed for {name}: {e}")

        if value == "high":
            return StrategicValue.HIGH
        elif value == "low":
            return StrategicValue.LOW
        return StrategicValue.MEDIUM

    def _heuristic_evaluate(self, name: str, stars: int, description: str = "") -> StrategicValue:
        """Heuristic evaluation when AI is not available - Conservative (Zalando-style)"""
        name_lower = name.lower()
        description_lower = description.lower()
        combined_text = f"{name_lower} {description_lower}".strip()
        deprecated_info = self._get_deprecated_info(name)

        if is_resource_like_repository(name, description):
            return StrategicValue.LOW

        high_signal_keywords = {
            "react", "vue", "angular", "node", "python", "kubernetes",
            "docker", "postgresql", "typescript", "rust", "terraform",
        }
        medium_signal_keywords = {
            "eslint", "babel", "firebase", "framework", "platform", "runtime",
            "database", "compiler", "linter", "lint", "testing", "test",
            "bundler", "build", "orchestration", "backend as a service",
        }

        # Very high bar for HIGH - must be industry standard
        if stars > 50000:
            if any(keyword in combined_text for keyword in high_signal_keywords):
                return StrategicValue.HIGH
            if any(keyword in combined_text for keyword in medium_signal_keywords):
                return StrategicValue.HIGH
            return StrategicValue.MEDIUM

        # MEDIUM - solid adoption but not dominant
        elif stars > 10000:
            if deprecated_info:
                return StrategicValue.MEDIUM
            if any(x in combined_text for x in ["typescript", "rust", "go", "kotlin", "swift"]):
                return StrategicValue.MEDIUM
            if any(keyword in combined_text for keyword in medium_signal_keywords):
                return StrategicValue.MEDIUM
            return StrategicValue.LOW  # Stars alone aren't enough

        elif stars > 1000:
            if deprecated_info:
                return StrategicValue.MEDIUM
            if any(keyword in combined_text for keyword in medium_signal_keywords):
                return StrategicValue.MEDIUM
            return StrategicValue.LOW

        # LOW - everything else
        return StrategicValue.LOW

    def _should_ignore(self, item: Any) -> bool:
        """Check if item should be ignored based on auto-ignore rules"""
        name_lower = item.name.lower()

        for ignore_pattern in self.auto_ignore:
            if ignore_pattern.lower() == name_lower:
                return True
            if name_lower.startswith(ignore_pattern.lower()):
                return True
            if ignore_pattern.lower() in name_lower and len(ignore_pattern) > 3:
                return True

        return False

    def _should_include(self, item: Any) -> bool:
        """Check if item should be included based on include_only"""
        if self.include_only is None:
            return True

        name_lower = item.name.lower()
        for include_pattern in self.include_only:
            if include_pattern.lower() == name_lower:
                return True
            if include_pattern.lower() in name_lower:
                return True

        return False

    def _get_canonical_name(self, name: str) -> str:
        """Get canonical name for deduplication"""
        name_lower = name.lower()
        for canonical, aliases in DUPLICATE_MERGE_GROUPS.items():
            if name_lower in [a.lower() for a in aliases]:
                return canonical
        return name_lower

    def _is_parent_of(self, parent: str, child: str) -> bool:
        """Check if parent is parent of child in hierarchy"""
        parent_lower = parent.lower()
        child_lower = child.lower()
        if parent_lower in PARENT_CHILD_HIERARCHY:
            return child_lower in [c.lower() for c in PARENT_CHILD_HIERARCHY[parent_lower]]
        return False

    def _get_deprecated_info(self, name: str) -> Optional[dict]:
        """Get deprecation info if item is deprecated"""
        name_lower = name.lower()
        return DEPRECATED_MAP.get(name_lower)

    def _dedupe_and_consolidate(self, items: List[Any]) -> List[Any]:
        """Deduplicate items and consolidate hierarchies"""
        seen_canonical: dict = {}
        result = []

        for item in items:
            canonical = self._get_canonical_name(item.name)
            
            is_parent_item = False
            is_child_item = False
            parent_name = None
            
            for parent, children in PARENT_CHILD_HIERARCHY.items():
                if item.name.lower() == parent:
                    is_parent_item = True
                if any(item.name.lower() == c.lower() for c in children):
                    is_child_item = True
                    parent_name = parent
            
            if canonical in seen_canonical:
                existing = seen_canonical[canonical]
                if item.stars > existing.stars:
                    existing.stars = max(existing.stars, item.stars)
                    if item.name not in getattr(existing, 'merged_names', []):
                        existing.merged_names.append(item.name)
                continue
            
            if is_child_item and parent_name:
                parent_canonical = self._get_canonical_name(parent_name)
                if parent_canonical in seen_canonical:
                    parent_item = seen_canonical[parent_canonical]
                    parent_item.stars = max(parent_item.stars, item.stars)
                    if item.name not in parent_item.merged_names:
                        parent_item.merged_names.append(item.name)
                    continue
            
            item.merged_names = [item.name]
            seen_canonical[canonical] = item
            result.append(item)

        return result

    def _get_strategic_value_from_item(self, item: Any) -> Optional[StrategicValue]:
        """Extract strategic value from item if already present (from classifier)"""
        # Check if item has strategic_value attribute and it's not None
        sv = getattr(item, 'strategic_value', None)
        if sv is not None:
            # Handle both string and StrategicValue enum types
            if isinstance(sv, StrategicValue):
                return sv
            sv_str = str(sv).lower().strip()
            if sv_str == 'high':
                return StrategicValue.HIGH
            elif sv_str == 'low':
                return StrategicValue.LOW
            else:
                return StrategicValue.MEDIUM
        return None

    def filter(self, items: List[Any]) -> List[FilteredItem]:
        """Filter items based on strategic value and config"""
        deduplicated = self._dedupe_and_consolidate(items)
        filtered = []

        for item in deduplicated:
            if self._should_ignore(item):
                continue

            if not self._should_include(item):
                continue

            # Try to get strategic value from classifier first (single-pass optimization)
            strategic_value = self._get_strategic_value_from_item(item)
            
            # Only fall back to AI evaluation if not already present
            if strategic_value is None:
                strategic_value = self._evaluate_strategic_value(
                    item.name,
                    item.stars,
                    item.description
                )

            if is_resource_like_repository(item.name, item.description):
                strategic_value = StrategicValue.LOW

            if strategic_value == StrategicValue.LOW:
                continue

            if item.confidence < self.min_confidence:
                continue

            deprecated_info = self._get_deprecated_info(item.name)
            is_deprecated = deprecated_info is not None
            replacement = deprecated_info.get("replacement") if deprecated_info else None
            canonical_name = self._get_canonical_name(item.name)
            final_name = CANONICAL_DISPLAY_NAMES.get(canonical_name, canonical_name.title() if canonical_name else item.name)

            filtered_item = FilteredItem(
                name=final_name,
                description=item.description,
                stars=item.stars,
                quadrant=item.quadrant,
                ring=item.ring,
                confidence=item.confidence,
                trend=item.trend,
                strategic_value=strategic_value,
                is_deprecated=is_deprecated,
                replacement=replacement,
                merged_names=getattr(item, 'merged_names', [])
            )

            for attr in ("market_score", "signals", "moved", "sources"):
                value = getattr(item, attr, None)
                if value is not None:
                    setattr(filtered_item, attr, value)
            filtered.append(filtered_item)

        if self.metrics["calls"]:
            logger.info(
                "LLM filter summary | calls=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s small_requests=%s tool_calls=%s",
                self.metrics["calls"],
                self.metrics["prompt_tokens"],
                self.metrics["completion_tokens"],
                self.metrics["total_tokens"],
                self.metrics["small_requests"],
                self.metrics["tool_calls"],
            )

        return filtered
