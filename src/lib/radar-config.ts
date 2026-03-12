import type { QuadrantConfig, RingConfig, Quadrant, Ring } from './types';

export const RADAR_SIZE = 800;

// Tech Noir palette
export const QUADRANTS: QuadrantConfig[] = [
  { id: 'platforms', name: 'Platforms', color: '#f2ede2', angle: 0 },
  { id: 'techniques', name: 'Techniques', color: '#d96d1f', angle: 90 },
  { id: 'tools', name: 'Tools', color: '#9d5a28', angle: 180 },
  { id: 'languages', name: 'Languages', color: '#8b8276', angle: 270 },
];

export const RINGS: RingConfig[] = [
  { id: 'hold', name: 'Hold', color: '#6c655d', radius: 350 },
  { id: 'assess', name: 'Assess', color: '#9d5a28', radius: 275 },
  { id: 'trial', name: 'Trial', color: '#d96d1f', radius: 200 },
  { id: 'adopt', name: 'Adopt', color: '#f2ede2', radius: 125 },
];

export const getQuadrantById = (id: Quadrant): QuadrantConfig => {
  const found = QUADRANTS.find(q => q.id === id);
  if (!found) {
    console.warn(`[radar-config] Unknown quadrant id: "${id}", falling back to "${QUADRANTS[0].id}"`);
    return QUADRANTS[0];
  }
  return found;
};

export const getRingById = (id: Ring): RingConfig => {
  const found = RINGS.find(r => r.id === id);
  if (!found) {
    console.warn(`[radar-config] Unknown ring id: "${id}", falling back to "${RINGS[0].id}"`);
    return RINGS[0];
  }
  return found;
};
