import { describe, expect, it } from 'vitest';
import { getRadarContentState } from './radar-view-state';

describe('getRadarContentState', () => {
  it('reports filtered-empty when data exists but no visible technologies remain', () => {
    expect(getRadarContentState(75, 0)).toEqual({
      title: 'No matching technologies',
      description: 'No technologies match the current search or filters. Try clearing or adjusting them.',
    });
  });

  it('reports data-empty when the dataset is empty', () => {
    expect(getRadarContentState(0, 0)).toEqual({
      title: 'No technologies found',
      description: 'No technologies were found. Try reloading the page.',
    });
  });
});
