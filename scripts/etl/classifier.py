"""AI Classifier for Technology Radar with JSON mode and schema validation"""

import os
import json
import re
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from openai import OpenAI
from openai.types.responses import ResponseFunctionToolCall
from pydantic import BaseModel, Field, field_validator


class ClassificationSchema(BaseModel):
    name: str
    quadrant: str
    ring: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    trend: str
    rationale: Optional[str] = None

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


@dataclass
class ClassificationResult:
    name: str
    quadrant: str
    ring: str
    description: str
    confidence: float
    trend: str
    rationale: str = ""
    raw_response: str = ""


class TechnologyClassifier:
    """AI-powered classifier for technology categorization with JSON mode"""

    QUADRANTS = ['platforms', 'techniques', 'tools', 'languages']
    RINGS = ['adopt', 'trial', 'assess', 'hold']
    TRENDS = ['up', 'down', 'stable', 'new']

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
- rationale: explanation for the classification"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30
    ):
        self.api_key = api_key or os.environ.get('SYNTHETIC_API_KEY')
        self.base_url = base_url or os.environ.get('SYNTHETIC_API_URL', 'https://api.synthetic.new/v1')
        self.model = model or os.environ.get('SYNTHETIC_MODEL', 'llama-3.3-70b')
        self.max_retries = max_retries
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("SYNTHETIC_API_KEY is required")
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
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
                    max_tokens=500,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                return self._parse_response(content, name)
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5
                    time.sleep(wait_time)
                else:
                    print(f"Error classifying {name} after {self.max_retries} attempts: {e}")
                    return self._fallback_classification(name, stars, hn_mentions, description)
        
        return self._fallback_classification(name, stars, hn_mentions, description)

    def classify_batch(
        self,
        technologies: List[Dict[str, Any]]
    ) -> List[ClassificationResult]:
        """Classify multiple technologies"""
        results = []
        
        for tech in technologies:
            result = self.classify_one(
                name=tech.get('name', ''),
                stars=tech.get('stars', 0),
                hn_mentions=tech.get('hn_mentions', 0),
                description=tech.get('description', '')
            )
            results.append(result)
            
        return results

    def _parse_response(self, content: str, name: str) -> ClassificationResult:
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
                rationale=data.get('rationale', '')
            )
            
            return ClassificationResult(
                name=validated.name,
                quadrant=validated.quadrant,
                ring=validated.ring,
                description=validated.description,
                confidence=validated.confidence,
                trend=validated.trend,
                rationale=validated.rationale or "",
                raw_response=content
            )
            
        except Exception as e:
            print(f"Schema validation error: {e}")
            return self._fallback_classification(name, 0, 0, "")

    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response, supporting both raw JSON and markdown fenced blocks"""
        
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
        
        json_match = re.search(r'\{[^{}]*"name"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
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
        elif stars > 1000 or hn_mentions > 10:
            ring = 'trial'
        elif stars > 100 or hn_mentions > 5:
            ring = 'assess'
        else:
            ring = 'hold'
            
        return ClassificationResult(
            name=name,
            quadrant='tools',
            ring=ring,
            description=description or f"{name} - technology with {stars} stars",
            confidence=0.5,
            trend='stable',
            rationale="Fallback classification based on heuristics",
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
        print(f"\n{result.name}:")
        print(f"  Quadrant: {result.quadrant}")
        print(f"  Ring: {result.ring}")
        print(f"  Trend: {result.trend}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Rationale: {result.rationale}")


if __name__ == "__main__":
    main()