import { useMemo } from 'react';
import type { Technology, Quadrant, Ring } from '@/lib/types';
import { QUADRANTS, RINGS, RADAR_SIZE } from '@/lib/radar-config';

interface BlipPosition {
  x: number;
  y: number;
  angle: number;
}

function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

export function useBlipPosition(technologies: Technology[]) {
  const positions = useMemo(() => {
    const center = RADAR_SIZE / 2;
    const quadrantMap = new Map<Quadrant, Technology[]>();
    const ringMap = new Map<Ring, Technology[]>();

    QUADRANTS.forEach(q => quadrantMap.set(q.id, []));
    RINGS.forEach(r => ringMap.set(r.id, []));

    technologies.forEach(tech => {
      quadrantMap.get(tech.quadrant)?.push(tech);
      ringMap.get(tech.ring)?.push(tech);
    });

    const result = new Map<string, BlipPosition>();

    technologies.forEach((tech, index) => {
      const quadrant = QUADRANTS.find(q => q.id === tech.quadrant);
      const ring = RINGS.find(r => r.id === tech.ring);

      if (!quadrant || !ring) return;

      const quadrantTechs = quadrantMap.get(tech.quadrant) || [];
      const techIndexInQuadrant = quadrantTechs.findIndex(t => t.id === tech.id);
      const totalInQuadrant = quadrantTechs.length;

      const ringTechs = ringMap.get(tech.ring) || [];
      const techIndexInRing = ringTechs.findIndex(t => t.id === tech.id);

      const hash = hashCode(tech.id);
      const angleOffset = (hash % 30) - 15;
      const angle = quadrant.angle + angleOffset;

      const ringRadius = ring.radius;
      const baseRadius = ringRadius * 0.5;
      const maxRadius = ringRadius * 0.85;
      const radiusStep = (maxRadius - baseRadius) / Math.max(totalInQuadrant - 1, 1);
      const radius = baseRadius + (techIndexInRing * radiusStep);

      const angleRad = (angle * Math.PI) / 180;
      const x = center + radius * Math.cos(angleRad);
      const y = center + radius * Math.sin(angleRad);

      result.set(tech.id, { x, y, angle });
    });

    return result;
  }, [technologies]);

  const getPosition = (techId: string): BlipPosition | undefined => {
    return positions.get(techId);
  };

  return { getPosition, positions };
}