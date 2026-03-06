import { describe, expect, it } from 'vitest';
import aiData from '../data/data.ai.json';
import { QUADRANTS, RADAR_SIZE, RINGS } from './radar-config';
import { calculateBlipPositions, calculateVisibleBlipPositions } from './blip-position';
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

  it('puts Linux inside the platforms sector', () => {
    const typedAiData = aiData as AIRadarData;
    const positions = calculateBlipPositions(typedAiData.technologies);
    const linux = typedAiData.technologies.find((technology) => technology.id === 'linux');
    const linuxPosition = positions.get('linux');
    const center = RADAR_SIZE / 2;

    expect(linux).toBeDefined();
    expect(linuxPosition).toBeDefined();

    if (!linux || !linuxPosition) {
      return;
    }

    const quadrant = QUADRANTS.find((value) => value.id === linux.quadrant);

    expect(quadrant).toBeDefined();

    if (!quadrant) {
      return;
    }

    const angle = (Math.atan2(linuxPosition.y - center, linuxPosition.x - center) * 180) / Math.PI;
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
});
