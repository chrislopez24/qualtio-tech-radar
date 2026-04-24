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
  it('surfaces the editorial workbench, metrics, presets, and mobile views', () => {
    const html = renderToStaticMarkup(<HomeClient initialData={radarData} />);

    expect(html).toContain('Editorial radar');
    expect(html).toContain('Market signals, filtered into adoption decisions.');
    expect(html).toContain('Visible');
    expect(html).toContain('Watchlist');
    expect(html).toContain('Strong signals');
    expect(html).toContain('Rising');
    expect(html).toContain('Needs review');
    expect(html).toContain('Explore');
    expect(html).toContain('Quality');
  });
});
