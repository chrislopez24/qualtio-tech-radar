import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { AITechnology } from '@/lib/types';
import { RadarSidebar } from './RadarSidebar';

const watchlistItem: AITechnology = {
  id: 'zig',
  name: 'Zig',
  quadrant: 'languages',
  ring: 'assess',
  description: 'Low-level language',
  trend: 'up',
  confidence: 0.72,
  updatedAt: '2026-03-05T00:00:00.000Z',
};

describe('RadarSidebar', () => {
  it('uses a compact desktop layout with inline views for technologies, watchlist and guide', () => {
    const html = renderToStaticMarkup(
      <RadarSidebar
        visibleTechnologies={[]}
        totalTechnologies={0}
        selectedTechnologyId={null}
        hoveredTechnologyId={null}
        watchlist={[watchlistItem]}
        totalWatchlistCount={1}
        filters={{ rings: [], quadrants: [], trends: [], minConfidence: null }}
        onToggleRing={() => {}}
        onToggleQuadrant={() => {}}
        onToggleTrend={() => {}}
        onSetMinConfidence={() => {}}
        onResetFilters={() => {}}
        onHoverTechnology={() => {}}
        onSelectTechnology={() => {}}
      />,
    );

    expect(html).toContain('h-auto');
    expect(html).toContain('lg:h-full');
    expect(html).toContain('Technologies');
    expect(html).toContain('Watchlist');
    expect(html).toContain('Guide');
    expect(html).toContain('Watchlist</span><span');
    expect(html).toContain('>1<');
  });
});
