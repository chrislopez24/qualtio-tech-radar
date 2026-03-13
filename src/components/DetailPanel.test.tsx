import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { AITechnology } from '@/lib/types';
import { DetailPanel } from './DetailPanel';

const richTechnology: AITechnology = {
  id: 'go',
  name: 'Go',
  quadrant: 'platforms',
  ring: 'adopt',
  description: 'A systems language.',
  trend: 'up',
  confidence: 0.91,
  updatedAt: '2026-03-05T00:00:00.000Z',
  whyNow: 'Demand is increasing for resilient cloud services.',
  useCases: ['API services', 'CLIs'],
  avoidWhen: ['Ultra-fast prototyping with no Go expertise'],
  risk: {
    security: 'Dependency governance is required.',
    lockIn: 'Low lock-in risk.',
  },
  owner: 'Platform Team',
  nextStep: 'Ship one pilot service.',
  nextReviewAt: '2026-06-01',
  evidence: ['https://go.dev/'],
  alternatives: ['Rust', 'Node.js'],
};

describe('DetailPanel', () => {
  it('renders actionable sections when metadata is present', () => {
    const html = renderToStaticMarkup(
      <DetailPanel technology={richTechnology} open anchor={{ x: 240, y: 180 }} onClose={() => {}} />,
    );

    expect(html).toContain('Why now');
    expect(html).toContain('Use cases');
    expect(html).toContain('Avoid when');
    expect(html).toContain('Risks');
    expect(html).toContain('Owner &amp; review');
    expect(html).toContain('Next step');
    expect(html).toContain('Evidence / alternatives');
    expect(html).toContain('data-detail-anchor="240:180"');
    expect(html).toContain('lg:block');
    expect(html).toContain('role="dialog"');
    expect(html).toContain('data-detail-overlay="true"');
  });

  it('does not render actionable headings when metadata is absent', () => {
    const html = renderToStaticMarkup(
      <DetailPanel
        technology={{
          id: 'legacy',
          name: 'Legacy',
          quadrant: 'tools',
          ring: 'assess',
          description: 'Legacy item',
          trend: 'stable',
          confidence: 0.5,
          updatedAt: '2026-03-05T00:00:00.000Z',
        }}
        open
        anchor={{ x: 240, y: 180 }}
        onClose={() => {}}
      />,
    );

    expect(html).not.toContain('Why now');
    expect(html).not.toContain('Use cases');
    expect(html).not.toContain('Avoid when');
  });

  it('renders provenance and freshness hints when present', () => {
    const html = renderToStaticMarkup(
      <DetailPanel
        technology={{
          ...richTechnology,
          sourceSummary: 'github + hn blended signals',
          signalFreshness: 'fresh in last 7 days',
        }}
        open
        anchor={{ x: 240, y: 180 }}
        onClose={() => {}}
      />,
    );

    expect(html).toContain('Data provenance');
    expect(html).toContain('github + hn blended signals');
    expect(html).toContain('Signal freshness');
    expect(html).toContain('fresh in last 7 days');
  });

  it('does not render provenance section when optional fields are absent', () => {
    const html = renderToStaticMarkup(
      <DetailPanel
        technology={{
          ...richTechnology,
          sourceSummary: undefined,
          signalFreshness: undefined,
        }}
        open
        anchor={{ x: 240, y: 180 }}
        onClose={() => {}}
      />,
    );

    expect(html).not.toContain('Data provenance');
    expect(html).not.toContain('Signal freshness');
  });

  it('renders evidence summary, source coverage and why-this-ring when present', () => {
    const html = renderToStaticMarkup(
      <DetailPanel
        technology={{
          ...richTechnology,
          sourceCoverage: 4,
          whyThisRing: 'Adopt because composite 88.4 is backed by external adoption evidence across 4 sources.',
          sourceFreshness: {
            freshestDays: 1,
            stalestDays: 2,
          },
          evidenceSummary: {
            sources: ['github', 'hackernews', 'deps_dev', 'osv'],
            metrics: ['reverse_dependents', 'tag_activity'],
            hasExternalAdoption: true,
            githubOnly: false,
          },
        }}
        open
        anchor={{ x: 240, y: 180 }}
        onClose={() => {}}
      />,
    );

    expect(html).toContain('Why this ring');
    expect(html).toContain('Source coverage');
    expect(html).toContain('4 sources');
    expect(html).toContain('Evidence summary');
    expect(html).toContain('reverse_dependents');
    expect(html).toContain('freshest 1d');
  });
});
