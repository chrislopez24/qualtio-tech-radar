import { describe, expect, it } from 'vitest';
import type { AITechnology } from './types';
import { filterTechnologies, type RadarFilterState } from './radar-filters';

const baseFilters: RadarFilterState = {
  rings: [],
  quadrants: [],
  trends: [],
  minConfidence: null,
};

const technologies: AITechnology[] = [
  {
    id: 'go',
    name: 'Go',
    quadrant: 'platforms',
    ring: 'adopt',
    description: 'Go language for backend systems',
    trend: 'up',
    githubStars: 100,
    hnMentions: 20,
    confidence: 0.9,
    updatedAt: '2026-03-05T10:00:00.000Z',
  },
  {
    id: 'rust',
    name: 'Rust',
    quadrant: 'platforms',
    ring: 'trial',
    description: 'Reliable systems language',
    trend: 'stable',
    githubStars: 80,
    hnMentions: 10,
    confidence: 0.7,
    updatedAt: '2026-03-05T10:00:00.000Z',
  },
  {
    id: 'vue',
    name: 'Vue',
    quadrant: 'tools',
    ring: 'assess',
    description: 'Frontend framework',
    trend: 'down',
    githubStars: 70,
    hnMentions: 6,
    confidence: 0.45,
    updatedAt: '2026-03-05T10:00:00.000Z',
  },
];

describe('filterTechnologies', () => {
  it('returns all technologies when no filters are applied', () => {
    const result = filterTechnologies(technologies, '', baseFilters);
    expect(result).toHaveLength(3);
  });

  it('applies ring and quadrant filters as an intersection', () => {
    const result = filterTechnologies(technologies, '', {
      ...baseFilters,
      rings: ['adopt', 'trial'],
      quadrants: ['platforms'],
    });

    expect(result.map((tech) => tech.id)).toEqual(['go', 'rust']);
  });

  it('filters by trend values', () => {
    const result = filterTechnologies(technologies, '', {
      ...baseFilters,
      trends: ['up'],
    });

    expect(result.map((tech) => tech.id)).toEqual(['go']);
  });

  it('filters by minimum confidence threshold', () => {
    const result = filterTechnologies(technologies, '', {
      ...baseFilters,
      minConfidence: 0.7,
    });

    expect(result.map((tech) => tech.id)).toEqual(['go', 'rust']);
  });

  it('combines search query with structured filters', () => {
    const result = filterTechnologies(technologies, 'systems', {
      ...baseFilters,
      rings: ['adopt'],
      trends: ['up'],
      minConfidence: 0.8,
    });

    expect(result.map((tech) => tech.id)).toEqual(['go']);
  });
});
