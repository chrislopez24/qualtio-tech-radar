import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Header } from './Header';

describe('Header', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('renders the Qualtio logo asset and radar label', () => {
    vi.stubEnv('NODE_ENV', 'production');

    const html = renderToStaticMarkup(
      <Header searchQuery="" onSearchChange={() => {}} />,
    );

    expect(html).toContain('/qualtio-tech-radar/logo.png');
    expect(html).toContain('Qualtio');
    expect(html).toContain('Tech Radar');
  });
});
