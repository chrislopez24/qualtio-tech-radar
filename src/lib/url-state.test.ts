import { describe, expect, it } from 'vitest';
import { parseRadarUrlState, serializeRadarUrlState } from './url-state';

describe('url-state', () => {
  it('parses query and filter state from URL search params', () => {
    const state = parseRadarUrlState(
      new URLSearchParams('q=react&rings=adopt,trial&quadrants=tools&trends=up,new&confidence=0.75'),
    );

    expect(state.searchQuery).toBe('react');
    expect(state.filters.rings).toEqual(['adopt', 'trial']);
    expect(state.filters.quadrants).toEqual(['tools']);
    expect(state.filters.trends).toEqual(['up', 'new']);
    expect(state.filters.minConfidence).toBe(0.75);
  });

  it('serializes compact URL search params and omits empty values', () => {
    const params = serializeRadarUrlState({
      searchQuery: 'react',
      filters: {
        rings: ['adopt'],
        quadrants: [],
        trends: ['up'],
        minConfidence: 0.6,
      },
    });

    expect(params.toString()).toBe('q=react&rings=adopt&trends=up&confidence=0.6');
  });
});
