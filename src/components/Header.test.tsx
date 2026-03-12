import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { Header } from './Header';

describe('Header', () => {
  it('renders the Qualtio logo asset and radar label', () => {
    const html = renderToStaticMarkup(
      <Header searchQuery="" onSearchChange={() => {}} />,
    );

    expect(html).toContain('/logo.png');
    expect(html).toContain('Qualtio');
    expect(html).toContain('Tech Radar');
  });
});
