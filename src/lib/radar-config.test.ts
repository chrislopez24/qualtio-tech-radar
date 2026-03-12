import { describe, expect, it } from 'vitest';
import { QUADRANTS, RINGS } from './radar-config';

describe('radar-config', () => {
  it('keeps visually distinct quadrant colors', () => {
    expect(new Set(QUADRANTS.map((quadrant) => quadrant.color)).size).toBe(4);
  });

  it('keeps visually distinct ring colors', () => {
    expect(new Set(RINGS.map((ring) => ring.color)).size).toBe(4);
  });

  it('preserves a warm brand accent in the radar palette', () => {
    expect(
      QUADRANTS.some((quadrant) => quadrant.color.toLowerCase() === '#f97316') ||
        RINGS.some((ring) => ring.color.toLowerCase() === '#f97316'),
    ).toBe(true);
  });
});
