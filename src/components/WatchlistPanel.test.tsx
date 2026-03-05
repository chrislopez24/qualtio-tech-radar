import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { AITechnology } from '@/lib/types';
import { WatchlistPanel } from './WatchlistPanel';

const watchlistItem: AITechnology = {
  id: 'django',
  name: 'Django',
  quadrant: 'tools',
  ring: 'assess',
  description: 'Python web framework',
  trend: 'stable',
  confidence: 0.7,
  updatedAt: '2026-03-05T00:00:00.000Z',
  owner: 'Internal Tools Team',
  nextStep: 'Standardize project template.',
  nextReviewAt: '2099-01-01',
};

describe('WatchlistPanel', () => {
  it('renders owner, action summary and review status badge', () => {
    const html = renderToStaticMarkup(
      <WatchlistPanel
        watchlist={[watchlistItem]}
        onSelectTechnology={() => {}}
      />,
    );

    expect(html).toContain('Owner: Internal Tools Team');
    expect(html).toContain('Action: Standardize project template.');
    expect(html).toContain('Due in');
  });

  it('renders fallback status when review date is missing', () => {
    const html = renderToStaticMarkup(
      <WatchlistPanel
        watchlist={[{ ...watchlistItem, nextReviewAt: undefined }]}
        onSelectTechnology={() => {}}
      />,
    );

    expect(html).toContain('No review date');
  });
});
