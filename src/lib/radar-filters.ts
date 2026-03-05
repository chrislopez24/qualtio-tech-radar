import type { AITechnology, Quadrant, Ring, Trend } from './types';
import { matchesTechnologySearch } from './radar-search';

export interface RadarFilterState {
  rings: Ring[];
  quadrants: Quadrant[];
  trends: Trend[];
  minConfidence: number | null;
}

export function filterTechnologies(
  technologies: AITechnology[],
  searchQuery: string,
  filters: RadarFilterState,
): AITechnology[] {
  const normalizedSearch = searchQuery.trim();
  const hasRingFilters = filters.rings.length > 0;
  const hasQuadrantFilters = filters.quadrants.length > 0;
  const hasTrendFilters = filters.trends.length > 0;
  const minConfidence = filters.minConfidence;
  const hasConfidenceFilter = minConfidence !== null;

  if (
    normalizedSearch.length === 0 &&
    !hasRingFilters &&
    !hasQuadrantFilters &&
    !hasTrendFilters &&
    !hasConfidenceFilter
  ) {
    return technologies;
  }

  return technologies.filter((technology) => {
    if (!matchesTechnologySearch(technology, normalizedSearch)) {
      return false;
    }

    if (hasRingFilters && !filters.rings.includes(technology.ring)) {
      return false;
    }

    if (hasQuadrantFilters && !filters.quadrants.includes(technology.quadrant)) {
      return false;
    }

    if (hasTrendFilters && !filters.trends.includes(technology.trend)) {
      return false;
    }

    if (minConfidence !== null && technology.confidence < minConfidence) {
      return false;
    }

    return true;
  });
}
