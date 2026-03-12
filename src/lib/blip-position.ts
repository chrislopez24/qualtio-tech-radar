import type { Technology } from './types';
import { QUADRANTS, RADAR_SIZE, RINGS } from './radar-config';

export interface BlipPosition {
  x: number;
  y: number;
  angle: number;
}

interface TooltipPositionInput {
  x: number;
  y: number;
  width: number;
  height?: number;
  radarSize?: number;
  margin?: number;
  offset?: number;
}

function hashCode(value: string): number {
  let hash = 0;

  for (let index = 0; index < value.length; index += 1) {
    const charCode = value.charCodeAt(index);
    hash = ((hash << 5) - hash) + charCode;
    hash |= 0;
  }

  return Math.abs(hash);
}

function pseudoRandom(seed: number, salt: number): number {
  const value = Math.sin(seed * 12.9898 + salt * 78.233) * 43758.5453;
  return value - Math.floor(value);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function roundCoordinate(value: number): number {
  return Number(value.toFixed(4));
}

export function getTooltipPosition({
  x,
  y,
  width,
  height = 26,
  radarSize = RADAR_SIZE,
  margin = 8,
  offset = 18,
}: TooltipPositionInput): { x: number; y: number } {
  const preferredX = x + offset;
  const fallbackX = x - width - offset;
  const unclampedX = preferredX + width > radarSize - margin ? fallbackX : preferredX;
  const clampedX = clamp(unclampedX, margin, radarSize - width - margin);
  const clampedY = clamp(y - 14, margin, radarSize - height - margin);

  return {
    x: clampedX,
    y: clampedY,
  };
}

function getRingBounds(ringId: Technology['ring']) {
  const ringIndex = RINGS.findIndex((ring) => ring.id === ringId);

  if (ringIndex === -1) {
    return null;
  }

  const outerRadius = RINGS[ringIndex].radius;
  const innerRadius = ringIndex === RINGS.length - 1 ? 0 : RINGS[ringIndex + 1].radius;

  return { innerRadius, outerRadius };
}

export function calculateBlipPositions(technologies: Technology[]): Map<string, BlipPosition> {
  const center = RADAR_SIZE / 2;
  const groupedTechnologies = new Map<string, Technology[]>();

  for (const technology of technologies) {
    const key = `${technology.quadrant}:${technology.ring}`;

    if (!groupedTechnologies.has(key)) {
      groupedTechnologies.set(key, []);
    }

    groupedTechnologies.get(key)?.push(technology);
  }

  for (const group of groupedTechnologies.values()) {
    group.sort((left, right) => left.id.localeCompare(right.id));
  }

  const result = new Map<string, BlipPosition>();

  for (const [key, group] of groupedTechnologies.entries()) {
    const [quadrantId, ringId] = key.split(':') as [Technology['quadrant'], Technology['ring']];
    const quadrant = QUADRANTS.find((value) => value.id === quadrantId);
    const ringBounds = getRingBounds(ringId);

    if (!quadrant || !ringBounds) {
      continue;
    }

    const { innerRadius, outerRadius } = ringBounds;
    const ringThickness = outerRadius - innerRadius;
    const radialPadding = Math.min(14, Math.max(4, ringThickness * 0.2));
    const minRadius = innerRadius + radialPadding;
    const maxRadius = Math.max(minRadius, outerRadius - radialPadding);

    const sectorPadding = 8;
    const sectorStart = (quadrant.angle - 90) - 45 + sectorPadding;
    const sectorSpan = 90 - (sectorPadding * 2);
    const sectorEnd = sectorStart + sectorSpan;

    const radialSlots = Math.max(1, Math.ceil(Math.sqrt(group.length)));
    const angularSlots = Math.max(1, Math.ceil(group.length / radialSlots));
    const angleStep = sectorSpan / angularSlots;
    const radiusStep = radialSlots > 1 ? (maxRadius - minRadius) / (radialSlots - 1) : 0;

    group.forEach((technology, index) => {
      const radialSlot = index % radialSlots;
      const angularSlot = Math.floor(index / radialSlots);
      const seed = hashCode(technology.id);

      const angleJitterRange = Math.min(3, angleStep * 0.25);
      const angleJitter = (pseudoRandom(seed, 1) - 0.5) * angleJitterRange;
      const baseAngle = sectorStart + angleStep * (angularSlot + 0.5);
      const angle = clamp(baseAngle + angleJitter, sectorStart, sectorEnd);

      const radiusJitterRange = Math.min(6, Math.max(radiusStep * 0.25, (maxRadius - minRadius) * 0.08));
      const radiusJitter = (pseudoRandom(seed, 2) - 0.5) * radiusJitterRange;
      const baseRadius = minRadius + radiusStep * radialSlot;
      const radius = clamp(baseRadius + radiusJitter, minRadius, maxRadius);

      const angleRad = (angle * Math.PI) / 180;
      const x = center + radius * Math.cos(angleRad);
      const y = center + radius * Math.sin(angleRad);

      result.set(technology.id, {
        x: roundCoordinate(x),
        y: roundCoordinate(y),
        angle: roundCoordinate(angle),
      });
    });
  }

  return result;
}

export function calculateVisibleBlipPositions(
  visibleTechnologies: Technology[],
  layoutTechnologies: Technology[] = visibleTechnologies,
): Map<string, BlipPosition> {
  const allPositions = calculateBlipPositions(layoutTechnologies);
  const visibleIds = new Set(visibleTechnologies.map((technology) => technology.id));
  const visiblePositions = new Map<string, BlipPosition>();

  for (const [technologyId, position] of allPositions.entries()) {
    if (visibleIds.has(technologyId)) {
      visiblePositions.set(technologyId, position);
    }
  }

  return visiblePositions;
}
