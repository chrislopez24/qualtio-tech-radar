import { describe, expect, it } from 'vitest';
import type { AITechnology } from './types';
import { matchesTechnologySearch } from './radar-search';

const technology: AITechnology = {
  id: 'react',
  name: 'React',
  quadrant: 'tools',
  ring: 'adopt',
  description: 'Component UI library.',
  trend: 'up',
  confidence: 0.9,
  updatedAt: '2026-03-13T00:00:00.000Z',
  whyNow: 'Design systems and app shells still converge on React.',
  useCases: ['Design systems', 'Admin panels'],
  alternatives: ['Vue'],
  owner: 'Frontend Platform',
  evidence: ['github:stars', 'deps_dev:reverse_dependents'],
};

describe('matchesTechnologySearch', () => {
  it('matches owner, whyNow, alternatives, use cases and evidence fields', () => {
    expect(matchesTechnologySearch(technology, 'frontend platform')).toBe(true);
    expect(matchesTechnologySearch(technology, 'design systems')).toBe(true);
    expect(matchesTechnologySearch(technology, 'vue')).toBe(true);
    expect(matchesTechnologySearch(technology, 'reverse_dependents')).toBe(true);
    expect(matchesTechnologySearch(technology, 'app shells')).toBe(true);
  });
});
