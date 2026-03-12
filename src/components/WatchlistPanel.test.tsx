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

  it('renders compact what changed block from shadow gate metadata', () => {
    const html = renderToStaticMarkup(
      <WatchlistPanel
        watchlist={[watchlistItem]}
        meta={{
          pipeline: {
            ringDistribution: {
              adopt: 1,
              trial: 2,
              assess: 0,
              hold: 1,
            },
            topAdded: [{ id: 'bun', name: 'Bun', ring: 'trial', marketScore: 91.4 }],
            topDropped: [{ id: 'vue', name: 'Vue', ring: 'assess', marketScore: 66.0 }],
          },
          shadowGate: {
            status: 'warn',
            addedCount: 3,
            filteredCount: 2,
            leaderTransitionSummary: {
              candidateCount: 2,
              promotedCount: 1,
            },
            candidateChanges: {
              llama: { leaderId: 'llama', changeType: 'added', consecutiveCount: 2 },
              mistral: { leaderId: 'mistral', changeType: 'removed', consecutiveCount: 1 },
            },
          },
        }}
        onSelectTechnology={() => {}}
      />,
    );

    expect(html).toContain('What changed');
    expect(html).toContain('WARN');
    expect(html).toContain('Added: 3');
    expect(html).toContain('Filtered: 2');
    expect(html).toContain('Ring mix');
    expect(html).toContain('adopt 1');
    expect(html).toContain('trial 2');
    expect(html).toContain('Added sample');
    expect(html).toContain('Bun');
    expect(html).toContain('Dropped sample');
    expect(html).toContain('Vue');
    expect(html).toContain('Leader transitions: 2 pending / 1 promoted');
    expect(html).toContain('Candidate transitions: 2');
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

  it('distinguishes an empty watchlist from a filtered-out watchlist', () => {
    const html = renderToStaticMarkup(
      <WatchlistPanel
        watchlist={[]}
        totalWatchlistCount={3}
        onSelectTechnology={() => {}}
      />,
    );

    expect(html).toContain('No watchlist entries match current filters.');
    expect(html).toContain('0 of 3 items');
    expect(html).not.toContain('No watchlist entries in current run.');
  });

  it('renders quality overview when ring and quadrant quality metadata are present', () => {
    const html = renderToStaticMarkup(
      <WatchlistPanel
        watchlist={[watchlistItem]}
        meta={{
          pipeline: {
            ringQuality: {
              adopt: { count: 4, avgMarketScore: 91, githubOnlyRatio: 0, resourceLikeCount: 0, editoriallyWeakCount: 0, topSuspicious: [], status: 'good' },
              trial: { count: 6, avgMarketScore: 68, githubOnlyRatio: 0.66, resourceLikeCount: 0, editoriallyWeakCount: 1, topSuspicious: [], status: 'bad' },
            },
            quadrantQuality: {
              tools: { count: 5, avgMarketScore: 74, githubOnlyRatio: 0.4, resourceLikeCount: 0, editoriallyWeakCount: 1, topSuspicious: [], status: 'warn' },
            },
          },
        }}
        onSelectTechnology={() => {}}
      />,
    );

    expect(html).toContain('Quality overview');
    expect(html).toContain('Adopt');
    expect(html).toContain('good');
    expect(html).toContain('Trial');
    expect(html).toContain('bad');
    expect(html).toContain('Tools');
    expect(html).toContain('warn');
  });
});
