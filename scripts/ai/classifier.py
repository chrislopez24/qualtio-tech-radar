"""AI Classifier for Technology Radar using Synthetic API"""

import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from openai import OpenAI


@dataclass
class ClassificationResult:
    name: str
    quadrant: str
    ring: str
    description: str
    confidence: float
    trend: str


class TechnologyClassifier:
    """AI-powered classifier for technology categorization"""

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
- trend: trend direction (up/down/stable/new)"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get('SYNTHETIC_API_KEY')
        self.base_url = base_url or os.environ.get('SYNTHETIC_API_URL', 'https://api.synthetic.new/v1')
        
        if not self.api_key:
            raise ValueError("SYNTHETIC_API_KEY is required")
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def classify_technology(self, name: str, stars: int = 0, hn_mentions: int = 0, 
                           description: str = "") -> ClassificationResult:
        """Classify a single technology"""
        
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

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            return self._parse_response(content, name)
            
        except Exception as e:
            print(f"Error classifying {name}: {e}")
            return self._fallback_classification(name, stars, hn_mentions, description)

    def classify_batch(self, technologies: List[Dict[str, Any]]) -> List[ClassificationResult]:
        """Classify multiple technologies"""
        results = []
        
        for tech in technologies:
            result = self.classify_technology(
                name=tech.get('name', ''),
                stars=tech.get('stars', 0),
                hn_mentions=tech.get('hn_mentions', 0),
                description=tech.get('description', '')
            )
            results.append(result)
            
        return results

    def _parse_response(self, content: str, name: str) -> ClassificationResult:
        """Parse AI response into ClassificationResult"""
        try:
            data = json.loads(content)
            
            return ClassificationResult(
                name=data.get('name', name),
                quadrant=self._normalize_quadrant(data.get('quadrant', 'tools')),
                ring=self._normalize_ring(data.get('ring', 'trial')),
                description=data.get('description', ''),
                confidence=float(data.get('confidence', 0.5)),
                trend=self._normalize_trend(data.get('trend', 'stable'))
            )
        except json.JSONDecodeError:
            return self._fallback_classification(name, 0, 0, "")

    def _normalize_quadrant(self, quadrant: str) -> str:
        """Ensure quadrant is valid"""
        quadrant = quadrant.lower().strip()
        for q in self.QUADRANTS:
            if q in quadrant:
                return q
        return 'tools'

    def _normalize_ring(self, ring: str) -> str:
        """Ensure ring is valid"""
        ring = ring.lower().strip()
        for r in self.RINGS:
            if r in ring:
                return r
        return 'trial'

    def _normalize_trend(self, trend: str) -> str:
        """Ensure trend is valid"""
        trend = trend.lower().strip()
        for t in self.TRENDS:
            if t in trend:
                return t
        return 'stable'

    def _fallback_classification(self, name: str, stars: int, hn_mentions: int, 
                                description: str) -> ClassificationResult:
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
            trend='stable'
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


if __name__ == "__main__":
    main()