import type { Quadrant, Ring, Trend } from './types';
import type { RadarFilterState } from './radar-filters';

interface RadarUrlState {
  searchQuery: string;
  filters: RadarFilterState;
}

const VALID_RINGS = new Set<Ring>(['adopt', 'trial', 'assess', 'hold']);
const VALID_QUADRANTS = new Set<Quadrant>(['platforms', 'techniques', 'tools', 'languages']);
const VALID_TRENDS = new Set<Trend>(['up', 'stable', 'new', 'down']);

export function parseRadarUrlState(params: URLSearchParams): RadarUrlState {
  return {
    searchQuery: params.get('q') ?? '',
    filters: {
      rings: parseList(params.get('rings'), VALID_RINGS),
      quadrants: parseList(params.get('quadrants'), VALID_QUADRANTS),
      trends: parseList(params.get('trends'), VALID_TRENDS),
      minConfidence: parseConfidence(params.get('confidence')),
    },
  };
}

export function serializeRadarUrlState(state: RadarUrlState): URLSearchParams {
  const params = new URLSearchParams();

  if (state.searchQuery.trim()) {
    params.set('q', state.searchQuery.trim());
  }
  if (state.filters.rings.length > 0) {
    params.set('rings', state.filters.rings.join(','));
  }
  if (state.filters.quadrants.length > 0) {
    params.set('quadrants', state.filters.quadrants.join(','));
  }
  if (state.filters.trends.length > 0) {
    params.set('trends', state.filters.trends.join(','));
  }
  if (state.filters.minConfidence !== null) {
    params.set('confidence', state.filters.minConfidence.toString());
  }

  return params;
}

function parseList<T extends string>(value: string | null, allowed: Set<T>): T[] {
  if (!value) {
    return [];
  }

  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item): item is T => allowed.has(item as T));
}

function parseConfidence(value: string | null): number | null {
  if (!value) {
    return null;
  }

  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return null;
  }

  return Math.max(0, Math.min(1, parsed));
}
