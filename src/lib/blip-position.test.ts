import { describe, expect, it } from 'vitest';
import aiData from '../data/data.ai.json';
import { QUADRANTS, RADAR_SIZE, RINGS } from './radar-config';
import {
  calculateBlipPositions,
  calculateVisibleBlipPositions,
  getTooltipPosition,
} from './blip-position';
import type { AIRadarData } from './types';

function getRingBounds(ringId: string) {
  const ringIndex = RINGS.findIndex((ring) => ring.id === ringId);

  if (ringIndex === -1) {
    throw new Error(`Unknown ring: ${ringId}`);
  }

  const outerRadius = RINGS[ringIndex].radius;
  const innerRadius = ringIndex === RINGS.length - 1 ? 0 : RINGS[ringIndex + 1].radius;

  return { innerRadius, outerRadius };
}

describe('calculateBlipPositions', () => {
  it('keeps each technology inside its ring band', () => {
    const typedAiData = aiData as AIRadarData;
    const positions = calculateBlipPositions(typedAiData.technologies);
    const center = RADAR_SIZE / 2;

    for (const technology of typedAiData.technologies) {
      const position = positions.get(technology.id);

      expect(position, `Missing position for ${technology.id}`).toBeDefined();

      if (!position) {
        continue;
      }

      const distanceToCenter = Math.hypot(position.x - center, position.y - center);
      const { innerRadius, outerRadius } = getRingBounds(technology.ring);

      expect(distanceToCenter).toBeGreaterThanOrEqual(innerRadius);
      expect(distanceToCenter).toBeLessThanOrEqual(outerRadius);
    }
  });

  it('puts a platforms technology inside the platforms sector', () => {
    const typedAiData = aiData as AIRadarData;
    const positions = calculateBlipPositions(typedAiData.technologies);
    const platformTech = typedAiData.technologies.find((technology) => technology.quadrant === 'platforms');
    const platformPosition = platformTech ? positions.get(platformTech.id) : undefined;
    const center = RADAR_SIZE / 2;

    expect(platformTech).toBeDefined();
    expect(platformPosition).toBeDefined();

    if (!platformTech || !platformPosition) {
      return;
    }

    const quadrant = QUADRANTS.find((value) => value.id === platformTech.quadrant);

    expect(quadrant).toBeDefined();

    if (!quadrant) {
      return;
    }

    const angle = (Math.atan2(platformPosition.y - center, platformPosition.x - center) * 180) / Math.PI;
    const normalizedAngle = angle < -180 ? angle + 360 : angle;
    const expectedCenter = quadrant.angle - 90;

    expect(normalizedAngle).toBeGreaterThanOrEqual(expectedCenter - 45);
    expect(normalizedAngle).toBeLessThanOrEqual(expectedCenter + 45);
  });

  it('keeps a visible technology in the same position when siblings are filtered out', () => {
    const allTechnologies = [
      {
        id: 'alpha',
        name: 'Alpha',
        quadrant: 'tools' as const,
        ring: 'trial' as const,
        description: 'Alpha',
      },
      {
        id: 'beta',
        name: 'Beta',
        quadrant: 'tools' as const,
        ring: 'trial' as const,
        description: 'Beta',
      },
    ];

    const positionsWithFullContext = calculateBlipPositions(allTechnologies);
    const positionsForVisibleSubset = calculateVisibleBlipPositions(
      [allTechnologies[0]],
      allTechnologies,
    );

    expect(positionsForVisibleSubset.get('alpha')).toEqual(positionsWithFullContext.get('alpha'));
  });

  it('rounds blip coordinates to stable precision for hydration', () => {
    const positions = calculateBlipPositions([
      {
        id: 'docker',
        name: 'Docker',
        quadrant: 'tools',
        ring: 'trial',
        description: 'Container tooling',
      },
    ]);

    const position = positions.get('docker');

    expect(position).toBeDefined();

    if (!position) {
      return;
    }

    expect(position.x).toBe(Number(position.x.toFixed(4)));
    expect(position.y).toBe(Number(position.y.toFixed(4)));
  });

  it('clamps tooltip positions inside the radar bounds', () => {
    expect(getTooltipPosition({ x: 10, y: 10, width: 120 })).toEqual({
      x: 28,
      y: 8,
    });

    expect(getTooltipPosition({ x: RADAR_SIZE - 10, y: 50, width: 120 })).toEqual({
      x: RADAR_SIZE - 148,
      y: 36,
    });
  });
});
