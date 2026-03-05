"""LLM decision cache with drift invalidation for reducing redundant LLM calls."""

import json
import logging
from pathlib import Path
from etl.checkpoint import safe_json_write
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
    
    def __init__(self, cache_path: Path, auto_flush: bool = True):
        """Initialize cache with the given file path.

        Args:
            cache_path: Path to the JSON cache file
            auto_flush: Persist on every write when True (CI-safe default)
        """
        self.cache_path = Path(cache_path)
        self.auto_flush = auto_flush
        self._cache: Dict[str, Any] = {}
        self._prefix_index: Dict[str, set[str]] = {}
        self._load()
    
    def _build_index(self) -> None:
        """Build a prefix index for faster lookups by name/model/prompt."""
        self._prefix_index = {}
        for key in self._cache.keys():
            parts = key.split("|", 3)
            if len(parts) != 4:
                continue
            prefix = "|".join(parts[:3])
            self._prefix_index.setdefault(prefix, set()).add(key)

    def _load(self) -> None:
        """Load cache from disk, tolerating corrupt files."""
        try:
            if self.cache_path.exists():
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
            self._build_index()
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.warning(f"Failed to load cache from {self.cache_path}: {e}")
            self._cache = {}
            self._prefix_index = {}
    
    def _save(self) -> None:
        """Save cache to disk, logging warnings on errors."""
        try:
            safe_json_write(self.cache_path, self._cache)
        except (IOError, OSError) as e:
            logger.warning(f"Failed to save cache to {self.cache_path}: {e}")

    def flush(self) -> None:
        """Persist cache content to disk explicitly."""
        self._save()
    
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
            prefix_without_json = f"{name}|{model}|{prompt_version}"
            indexed_keys = self._prefix_index.get(prefix_without_json, set())

            for key in indexed_keys:
                value = self._cache.get(key)
                if value is None:
                    continue

                # Extract cached features from key
                try:
                    features_json = key[len(prefix_without_json) + 1:]
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
            parts = key.split("|", 3)
            if len(parts) == 4:
                prefix = "|".join(parts[:3])
                self._prefix_index.setdefault(prefix, set()).add(key)

            if self.auto_flush:
                self._save()
        except Exception as e:
            logger.warning(f"Failed to cache value for key {key}: {e}")
