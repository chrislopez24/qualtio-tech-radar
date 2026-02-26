import { describe, expect, it } from 'vitest';
import aiData from '../data/data.ai.json';
import { QUADRANTS, RADAR_SIZE, RINGS } from './radar-config';
import { calculateBlipPositions } from './blip-position';

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
    const positions = calculateBlipPositions(aiData.technologies);
    const center = RADAR_SIZE / 2;

    for (const technology of aiData.technologies) {
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
    const positions = calculateBlipPositions(aiData.technologies);
    const linux = aiData.technologies.find((technology) => technology.id === 'linux');
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
});
