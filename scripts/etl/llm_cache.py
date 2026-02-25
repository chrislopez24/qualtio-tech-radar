"""LLM decision cache with drift invalidation for reducing redundant LLM calls."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LLMDecisionCache:
    """Cache for LLM decisions with signal drift-based invalidation.
    
    The cache stores LLM decisions keyed by technology name, model, prompt version,
    and rounded signal features. It allows cache hits when signals drift within
    a configurable threshold, reducing redundant LLM calls.
    
    Error handling:
    - Corrupt cache files are tolerated (returns miss)
    - Read errors result in cache miss (never blocks pipeline)
    - Write errors are logged as warnings only
    """
    
    def __init__(self, cache_path: Path):
        """Initialize cache with the given file path.
        
        Args:
            cache_path: Path to the JSON cache file
        """
        self.cache_path = Path(cache_path)
        self._cache: Dict[str, Any] = {}
        self._load()
    
    def _load(self) -> None:
        """Load cache from disk, tolerating corrupt files."""
        try:
            if self.cache_path.exists():
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.warning(f"Failed to load cache from {self.cache_path}: {e}")
            self._cache = {}
    
    def _save(self) -> None:
        """Save cache to disk, logging warnings on errors."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2)
        except (IOError, OSError) as e:
            logger.warning(f"Failed to save cache to {self.cache_path}: {e}")
    
    def _round_features(self, features: Dict[str, float], precision: float = 1.0) -> Dict[str, float]:
        """Round features to reduce cache fragmentation.
        
        Args:
            features: Dictionary of feature names to float values
            precision: Rounding precision (default 1.0 for integer rounding)
        
        Returns:
            Dictionary with rounded feature values
        """
        return {k: round(v / precision) * precision for k, v in features.items()}
    
    def _calculate_drift(
        self, 
        features1: Dict[str, float], 
        features2: Dict[str, float]
    ) -> float:
        """Calculate total drift between two feature sets.
        
        Uses sum of absolute differences across all feature keys.
        Missing keys in either set are treated as having value 0.
        
        Args:
            features1: First feature dictionary
            features2: Second feature dictionary
        
        Returns:
            Total drift value
        """
        all_keys = set(features1.keys()) | set(features2.keys())
        total_drift = 0.0
        
        for key in all_keys:
            v1 = features1.get(key, 0.0)
            v2 = features2.get(key, 0.0)
            total_drift += abs(v1 - v2)
        
        return total_drift
    
    def make_key(
        self, 
        name: str, 
        model: str, 
        prompt_version: str, 
        features: Dict[str, float]
    ) -> str:
        """Create a cache key from inputs.
        
        The key includes canonical name, model id, prompt version,
        and rounded signal features bucket.
        
        Args:
            name: Canonical technology name
            model: Model identifier
            prompt_version: Prompt version string
            features: Signal features dictionary
        
        Returns:
            String cache key
        """
        rounded = self._round_features(features)
        features_str = json.dumps(rounded, sort_keys=True)
        return f"{name}|{model}|{prompt_version}|{features_str}"
    
    def get_if_fresh(
        self,
        name: str,
        model: str,
        prompt_version: str,
        features: Dict[str, float],
        max_drift: float,
    ) -> Optional[Any]:
        """Get cached value if it exists and drift is within threshold.
        
        Searches for a cache entry matching the name, model, and prompt version,
        with signal drift below the max_drift threshold.
        
        Args:
            name: Technology name to look up
            model: Model identifier
            prompt_version: Prompt version
            features: Current signal features
            max_drift: Maximum allowable drift for a cache hit
        
        Returns:
            Cached value if found and fresh, None otherwise
        """
        try:
            prefix = f"{name}|{model}|{prompt_version}|"
            
            for key, value in self._cache.items():
                if not key.startswith(prefix):
                    continue
                
                # Extract cached features from key
                try:
                    features_json = key[len(prefix):]
                    cached_features = json.loads(features_json)
                    
                    # Calculate drift
                    drift = self._calculate_drift(features, cached_features)
                    
                    if drift <= max_drift:
                        logger.debug(f"Cache hit for {name}: drift={drift:.2f} <= {max_drift}")
                        return value
                except (json.JSONDecodeError, ValueError):
                    # Malformed cache entry, skip
                    continue
            
            return None
        except Exception as e:
            logger.warning(f"Cache lookup error for {name}: {e}")
            return None
    
    def put(self, key: str, value: Any) -> None:
        """Store a value in the cache.
        
        Args:
            key: Cache key from make_key()
            value: Value to cache (must be JSON serializable)
        """
        try:
            self._cache[key] = value
            self._save()
        except Exception as e:
            logger.warning(f"Failed to cache value for key {key}: {e}")
