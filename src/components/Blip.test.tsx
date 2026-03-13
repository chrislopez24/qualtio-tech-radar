import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { AITechnology } from '@/lib/types';
import { Blip } from './Blip';

const selectedTechnology: AITechnology = {
  id: 'vercel',
  name: 'Vercel',
  quadrant: 'platforms',
  ring: 'trial',
  description: 'Frontend cloud platform.',
  trend: 'up',
  confidence: 0.85,
  updatedAt: '2026-03-05T00:00:00.000Z',
};

describe('Blip', () => {
  it('keeps selected blips color-led without a white core fill', () => {
    const html = renderToStaticMarkup(
      <svg>
        <Blip
          technology={selectedTechnology}
          x={240}
          y={160}
          isSelected
          isFiltered={false}
          isHoveredExternal={false}
          onHoverChange={() => {}}
          onSelect={() => {}}
        />
      </svg>,
    );

    expect(html).toContain('stroke="#22d3ee"');
    expect(html).not.toContain('fill="#fff"');
    expect(html).not.toContain('fill="#f6f1e8"');
  });
});
