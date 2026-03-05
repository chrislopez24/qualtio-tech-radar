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
  return technologies.filter((technology) => {
    if (!matchesTechnologySearch(technology, searchQuery)) {
      return false;
    }

    if (filters.rings.length > 0 && !filters.rings.includes(technology.ring)) {
      return false;
    }

    if (filters.quadrants.length > 0 && !filters.quadrants.includes(technology.quadrant)) {
      return false;
    }

    if (filters.trends.length > 0 && !filters.trends.includes(technology.trend)) {
      return false;
    }

    if (filters.minConfidence !== null && technology.confidence < filters.minConfidence) {
      return false;
    }

    return true;
  });
}
