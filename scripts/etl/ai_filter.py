"""AI-powered strategic filter for technology radar items

This module provides strategic value filtering to reduce noise in the radar
by filtering out low-value items like utility libraries.
"""

import os
import json
import logging
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


class AITechnologyFilter:
    """AI-powered filter for technology radar items based on strategic value"""

    SYSTEM_PROMPT = """You are a technology strategic analyst. Your task is to evaluate
technologies for their strategic value to a tech radar.

Evaluate based on:
- Business impact and adoption
- Strategic importance to the organization
- Long-term viability and maintenance
- Developer experience and ecosystem

Categorize into:
- HIGH: Core technologies with significant business impact, widely adopted
- MEDIUM: Useful tools but not critical, moderate adoption
- LOW: Utility libraries, small packages, or niche technologies

Respond with JSON only: {"strategic_value": "high|medium|low", "reason": "brief explanation"}"""

    def __init__(self, config: FilterConfig):
        self.config = config
        self.auto_ignore = set(config.auto_ignore) if config.auto_ignore else set(DEFAULT_AUTO_IGNORE)
        self.include_only = set(config.include_only) if config.include_only else None
        self.min_confidence = config.min_confidence

        self._client: Optional[OpenAI] = None
        if os.environ.get("SYNTHETIC_API_KEY"):
            self._client = OpenAI(
                api_key=os.environ.get("SYNTHETIC_API_KEY"),
                base_url=os.environ.get("SYNTHETIC_API_URL", "https://api.synthetic.new/v1")
            )

    def _evaluate_strategic_value(self, name: str, stars: int, description: str) -> StrategicValue:
        """Evaluate strategic value using AI or heuristics"""
        if self._client:
            try:
                return self._ai_evaluate(name, stars, description)
            except Exception as e:
                logger.warning(f"AI evaluation failed for {name}, falling back to heuristic: {e}")

        return self._heuristic_evaluate(name, stars)

    def _ai_evaluate(self, name: str, stars: int, description: str) -> StrategicValue:
        """Use AI to evaluate strategic value"""
        prompt = f"""Evaluate this technology:

Name: {name}
Description: {description}
GitHub Stars: {stars}

Consider the strategic value for a tech radar."""

        response = self._client.chat.completions.create(
            model=os.environ.get("SYNTHETIC_MODEL", "llama-3.3-70b"),
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=200
        )

        content = response.choices[0].message.content
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
            return self._heuristic_evaluate(name, stars)

        if value == "high":
            return StrategicValue.HIGH
        elif value == "low":
            return StrategicValue.LOW
        return StrategicValue.MEDIUM

    def _heuristic_evaluate(self, name: str, stars: int) -> StrategicValue:
        """Heuristic evaluation when AI is not available"""
        name_lower = name.lower()

        if stars > 50000:
            return StrategicValue.HIGH
        elif stars > 5000:
            if any(x in name_lower for x in ["react", "vue", "angular", "node", "python", "rust", "go", "java"]):
                return StrategicValue.HIGH
            return StrategicValue.MEDIUM
        elif stars > 500:
            return StrategicValue.MEDIUM

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

    def filter(self, items: List[Any]) -> List[FilteredItem]:
        """Filter items based on strategic value and config"""
        filtered = []

        for item in items:
            if self._should_ignore(item):
                continue

            if not self._should_include(item):
                continue

            strategic_value = self._evaluate_strategic_value(
                item.name,
                item.stars,
                item.description
            )

            if strategic_value == StrategicValue.LOW:
                continue

            if item.confidence < self.min_confidence:
                continue

            filtered_item = FilteredItem(
                name=item.name,
                description=item.description,
                stars=item.stars,
                quadrant=item.quadrant,
                ring=item.ring,
                confidence=item.confidence,
                trend=item.trend,
                strategic_value=strategic_value
            )
            filtered.append(filtered_item)

        return filtered