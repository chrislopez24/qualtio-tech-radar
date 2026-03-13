import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { AIRadarData } from '@/lib/types';
import { HomeClient } from './HomeClient';

const radarData: AIRadarData = {
  updatedAt: '2026-03-13T00:00:00.000Z',
  technologies: [
    {
      id: 'react',
      name: 'React',
      quadrant: 'tools',
      ring: 'adopt',
      description: 'Component library',
      trend: 'up',
      confidence: 0.91,
      updatedAt: '2026-03-13T00:00:00.000Z',
    },
  ],
  watchlist: [],
  meta: {},
};

describe('HomeClient', () => {
  it('surfaces first-viewport guide content and presets', () => {
    const html = renderToStaticMarkup(<HomeClient initialData={radarData} />);

    expect(html).toContain('How to read this radar');
    expect(html).toContain('Strong signals');
    expect(html).toContain('Rising bets');
    expect(html).toContain('Needs review');
  });
});
