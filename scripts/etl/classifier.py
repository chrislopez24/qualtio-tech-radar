"""AI Classifier for Technology Radar with JSON mode and schema validation"""

import os
import json
import re
import time
import numbers
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from etl.quadrant_logic import infer_quadrant
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ClassificationSchema(BaseModel):
    name: str
    quadrant: str
    ring: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    trend: str
    rationale: Optional[str] = None
    strategic_value: str = "medium"

    @field_validator('quadrant')
    @classmethod
    def validate_quadrant(cls, v):
        valid = {'platforms', 'techniques', 'tools', 'languages'}
        v_lower = v.lower().strip()
        for q in valid:
            if q in v_lower:
                return q
        return 'tools'

    @field_validator('ring')
    @classmethod
    def validate_ring(cls, v):
        valid = {'adopt', 'trial', 'assess', 'hold'}
        v_lower = v.lower().strip()
        for r in valid:
            if r in v_lower:
                return r
        return 'trial'

    @field_validator('trend')
    @classmethod
    def validate_trend(cls, v):
        valid = {'up', 'down', 'stable', 'new'}
        v_lower = v.lower().strip()
        for t in valid:
            if t in v_lower:
                return t
        return 'stable'

    @field_validator('strategic_value')
    @classmethod
    def validate_strategic_value(cls, v):
        valid = {'high', 'medium', 'low'}
        v_lower = v.lower().strip()
        for sv in valid:
            if sv in v_lower:
                return sv
        return 'medium'


@dataclass
class ClassificationResult:
    name: str
    quadrant: str
    ring: str
    description: str
    confidence: float
    trend: str
    rationale: str = ""
    strategic_value: str = "medium"
    raw_response: str = ""


class TechnologyClassifier:
    """AI-powered classifier for technology categorization with JSON mode"""

    QUADRANTS = ['platforms', 'techniques', 'tools', 'languages']
    RINGS = ['adopt', 'trial', 'assess', 'hold']
    TRENDS = ['up', 'down', 'stable', 'new']

    MODEL_TIMEOUTS = {
        "hf:minimaxai/minimax-m2.5": 60,
        "hf:moonshotai/kimi-k2.5": 120,
    }

    SYSTEM_PROMPT = """You are a technology analyst specializing in tech radar categorization.
Your task is to classify technologies into the appropriate quadrant and ring based on their popularity and maturity.

Quadrants:
- platforms: Infrastructure, cloud, and runtime platforms
- techniques: Development methodologies, patterns, and practices
- tools: Libraries, frameworks, and development tools
- languages: Programming languages

Rings:
- adopt: Proven technologies widely used in production
- trial: Emerging technologies being validated in production
- assess: Technologies being explored/researched
- hold: Technologies in decline or with issues

Trends:
- up: Growing in popularity
- down: Declining in popularity
- stable: Consistent popularity
- new: Recently emerged

Provide a JSON response with:
- name: technology name
- quadrant: recommended quadrant
- ring: recommended ring  
- description: brief description (50-100 words)
- confidence: confidence score (0-1)
- trend: trend direction (up/down/stable/new)
- rationale: explanation for the classification
- strategic_value: strategic importance (high/medium/low)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30,
        batch_size: int = 50
    ):
        self.api_key = api_key or os.environ.get('SYNTHETIC_API_KEY')
        self.base_url = base_url or os.environ.get('SYNTHETIC_API_URL', 'https://api.synthetic.new/v1')
        self.model = model or os.environ.get('SYNTHETIC_MODEL', 'hf:MiniMaxAI/MiniMax-M2.5')
        self.max_retries = max_retries
        self.timeout = self._resolve_timeout(timeout)
        self.batch_size = batch_size

        
        if not self.api_key:
            raise ValueError("SYNTHETIC_API_KEY is required")
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        self.metrics: Dict[str, int] = {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "small_requests": 0,
            "tool_calls": 0,
        }

    def _resolve_timeout(self, explicit_timeout: int) -> int:
        if explicit_timeout != 30:
            return explicit_timeout

        model_key = (self.model or "").lower()
        for prefix, timeout in self.MODEL_TIMEOUTS.items():
            if model_key.startswith(prefix):
                return timeout

        return explicit_timeout

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
            "LLM classify request metrics | name=%s model=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s prompt_chars=%s completion_chars=%s tool_calls=%s finish_reason=%s small_request=%s",
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

    def classify_one(
        self,
        name: str,
        stars: int = 0,
        hn_mentions: int = 0,
        description: str = ""
    ) -> ClassificationResult:
        """Classify a single technology with retry logic"""
        
        prompt = f"""Classify this technology:

Name: {name}
Description: {description}
GitHub Stars: {stars}
Hacker News Mentions: {hn_mentions}

Consider:
- High stars (>10k) and mentions suggest 'adopt' ring
- Medium stars (1k-10k) suggest 'trial' ring
- Low stars but growing suggest 'assess' ring
- Declining activity suggests 'hold' ring

Respond with JSON only."""

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=8000,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                self._log_request_metrics(name, prompt, response, content or "")
                return self._parse_response(content, name)
                
            except RateLimitError as e:
                logger.warning(f"Rate limit exceeded for {name}, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    time.sleep(wait_time)
                else:
                    logger.error(f"Rate limit error classifying {name} after {self.max_retries} attempts: {e}")
                    return self._fallback_classification(name, stars, hn_mentions, description)
                    
            except APITimeoutError as e:
                logger.warning(f"API timeout for {name}, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 3
                    time.sleep(wait_time)
                else:
                    logger.error(f"Timeout error classifying {name} after {self.max_retries} attempts: {e}")
                    return self._fallback_classification(name, stars, hn_mentions, description)
                    
            except APIConnectionError as e:
                logger.warning(f"Connection error for {name}, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 3
                    time.sleep(wait_time)
                else:
                    logger.error(f"Connection error classifying {name} after {self.max_retries} attempts: {e}")
                    return self._fallback_classification(name, stars, hn_mentions, description)
                    
            except Exception as e:
                logger.error(f"Unexpected error classifying {name}: {e}")
                return self._fallback_classification(name, stars, hn_mentions, description)
        
        return self._fallback_classification(name, stars, hn_mentions, description)

    def classify_batch(
        self,
        technologies: List[Dict[str, Any]]
    ) -> List[ClassificationResult]:
        """Classify multiple technologies with configurable batch size"""
        results = []
        
        for i in range(0, len(technologies), self.batch_size):
            batch = technologies[i:i + self.batch_size]
            logger.info(f"Processing batch {i // self.batch_size + 1}: {len(batch)} technologies")
            
            for tech in batch:
                result = self.classify_one(
                    name=tech.get('name', ''),
                    stars=tech.get('stars', 0),
                    hn_mentions=tech.get('hn_mentions', 0),
                    description=tech.get('description', '')
                )
                results.append(result)

        if self.metrics["calls"]:
            logger.info(
                "LLM classify summary | calls=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s small_requests=%s tool_calls=%s",
                self.metrics["calls"],
                self.metrics["prompt_tokens"],
                self.metrics["completion_tokens"],
                self.metrics["total_tokens"],
                self.metrics["small_requests"],
                self.metrics["tool_calls"],
            )
             
        return results

    def _parse_response(self, content: Optional[str], name: str) -> ClassificationResult:
        """Parse AI response into ClassificationResult with schema validation"""
        
        data = self._extract_json(content)
        
        if data is None:
            return self._fallback_classification(name, 0, 0, "")
        
        try:
            validated = ClassificationSchema(
                name=data.get('name', name),
                quadrant=data.get('quadrant', 'tools'),
                ring=data.get('ring', 'trial'),
                description=data.get('description', ''),
                confidence=float(data.get('confidence', 0.5)),
                trend=data.get('trend', 'stable'),
                rationale=data.get('rationale', ''),
                strategic_value=data.get('strategic_value', 'medium')
            )
            
            return ClassificationResult(
                name=validated.name,
                quadrant=validated.quadrant,
                ring=validated.ring,
                description=validated.description,
                confidence=validated.confidence,
                trend=validated.trend,
                rationale=validated.rationale or "",
                strategic_value=validated.strategic_value,
                raw_response=content or ""
            )
            
        except Exception as e:
            logger.warning(f"Schema validation error for {name}: {e}")
            return self._fallback_classification(name, 0, 0, "")

    def _extract_json(self, content: Optional[str]) -> Optional[Dict[str, Any]]:
        """Extract JSON from response, supporting both raw JSON and markdown fenced blocks"""

        if not content:
            return None
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        fenced_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if fenced_match:
            try:
                return json.loads(fenced_match.group(1))
            except json.JSONDecodeError:
                pass
        
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if isinstance(data, dict) and 'name' in data:
                    return data
            except json.JSONDecodeError:
                pass
        
        return None

    def _fallback_classification(
        self,
        name: str,
        stars: int,
        hn_mentions: int,
        description: str
    ) -> ClassificationResult:
        """Fallback classification based on heuristics"""
        
        if stars > 10000 or hn_mentions > 50:
            ring = 'adopt'
            strategic_value = 'high'
        elif stars > 1000 or hn_mentions > 10:
            ring = 'trial'
            strategic_value = 'medium'
        elif stars > 100 or hn_mentions > 5:
            ring = 'assess'
            strategic_value = 'medium'
        else:
            ring = 'hold'
            strategic_value = 'low'

        # Use infer_quadrant instead of hardcoded 'tools'
        _ns = type('_NS', (), {'name': name, 'description': description or '', 'language': '', 'topics': []})()
        inferred_quadrant = infer_quadrant(_ns)

        return ClassificationResult(
            name=name,
            quadrant=inferred_quadrant,
            ring=ring,
            description=description or f"{name} - technology with {stars} stars",
            confidence=0.5,
            trend='stable',
            rationale="Fallback classification based on heuristics",
            strategic_value=strategic_value,
            raw_response=""
        )


def main():
    """Test the classifier"""
    classifier = TechnologyClassifier()
    
    test_techs = [
        {'name': 'React', 'stars': 220000, 'hn_mentions': 100, 'description': 'UI library'},
        {'name': 'Rust', 'stars': 95000, 'hn_mentions': 50, 'description': 'Systems language'},
    ]
    
    results = classifier.classify_batch(test_techs)
    
    for result in results:
        logger.info(f"\n{result.name}:")
        logger.info(f"  Quadrant: {result.quadrant}")
        logger.info(f"  Ring: {result.ring}")
        logger.info(f"  Trend: {result.trend}")
        logger.info(f"  Confidence: {result.confidence:.2f}")
        logger.info(f"  Rationale: {result.rationale}")


if __name__ == "__main__":
    main()
