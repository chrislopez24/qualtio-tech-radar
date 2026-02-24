"""Main Pipeline for Tech Radar Data Collection and Processing"""

import os
import sys
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Set
from dotenv import load_dotenv

load_dotenv()

from scraper.github import GitHubScraper
from scraper.hackernews import HackerNewsScraper
from ai.classifier import TechnologyClassifier


def load_config(config_path: str = "scripts/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def deduplicate_technologies(github_techs: List[Dict], hn_techs: List[Dict]) -> List[Dict]:
    """Deduplicate technologies from multiple sources"""
    seen: Set[str] = set()
    unique_techs: List[Dict] = []
    
    for tech in github_techs + hn_techs:
        name = tech.get('name', '').lower().strip()
        if name and name not in seen:
            seen.add(name)
            unique_techs.append(tech)
            
    return unique_techs


def normalize_technologies(repos: List[Any], hn_posts: List[Any]) -> List[Dict]:
    """Normalize technology data from different sources"""
    tech_map: Dict[str, Dict] = {}
    
    for repo in repos:
        name = repo.name
        if name not in tech_map:
            tech_map[name] = {
                'name': name,
                'description': repo.description,
                'stars': repo.stars,
                'forks': repo.forks,
                'language': repo.language,
                'topics': repo.topics,
                'url': repo.url,
                'hn_mentions': 0
            }
        else:
            tech_map[name]['stars'] = max(tech_map[name]['stars'], repo.stars)
            
    for post in hn_posts:
        title = post.title.lower()
        
        for name, tech in tech_map.items():
            if name.lower() in title:
                tech['hn_mentions'] += 1
                
    return list(tech_map.values())


def run_pipeline(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run the complete data pipeline"""
    print("=" * 60)
    print("Tech Radar Data Pipeline")
    print("=" * 60)
    
    print("\n[1/5] Loading configuration...")
    min_stars = config['github']['min_stars']
    max_repos = config['github']['max_repos']
    hn_min_points = config['hackernews']['min_points']
    hn_max_posts = config['hackernews']['max_posts']
    max_technologies = config['radar']['max_technologies']
    
    print(f"\n[2/5] Fetching GitHub trending repositories...")
    github_scraper = GitHubScraper()
    repos = github_scraper.get_trending_repos(min_stars=min_stars, limit=max_repos)
    print(f"  Found {len(repos)} repositories")
    
    print(f"\n[3/5] Fetching Hacker News tech posts...")
    hn_scraper = HackerNewsScraper()
    hn_posts = hn_scraper.search_tech_posts(min_points=hn_min_points, limit=hn_max_posts)
    print(f"  Found {len(hn_posts)} tech posts")
    
    print(f"\n[4/5] Normalizing and deduplicating technologies...")
    technologies = normalize_technologies(repos, hn_posts)
    technologies = deduplicate_technologies(technologies, [])
    technologies = technologies[:max_technologies]
    print(f"  {len(technologies)} unique technologies")
    
    print(f"\n[5/5] Classifying technologies with AI...")
    classifier = TechnologyClassifier()
    results = classifier.classify_batch(technologies)
    
    ai_technologies = []
    for result in results:
        tech = next((t for t in technologies if t['name'].lower() == result.name.lower()), None)
        
        ai_technologies.append({
            'id': result.name.lower().replace(' ', '-'),
            'name': result.name,
            'quadrant': result.quadrant,
            'ring': result.ring,
            'description': result.description,
            'moved': 0,
            'trend': result.trend,
            'githubStars': tech['stars'] if tech else 0,
            'hnMentions': tech['hn_mentions'] if tech else 0,
            'confidence': result.confidence,
            'updatedAt': datetime.now().isoformat()
        })
    
    output = {
        'updatedAt': datetime.now().isoformat(),
        'technologies': ai_technologies
    }
    
    return output


def save_output(output: Dict[str, Any], output_path: str):
    """Save output to JSON file"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
        
    print(f"\nOutput saved to: {output_path}")


def main():
    """Main entry point"""
    try:
        config = load_config()
        
        output = run_pipeline(config)
        
        output_path = config['output']['ai_data_file']
        save_output(output, output_path)
        
        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()