import type { QuadrantConfig, RingConfig, Quadrant, Ring } from './types';

export const RADAR_SIZE = 800;

// Qualtio shell + high-legibility data-viz palette
export const QUADRANTS: QuadrantConfig[] = [
  { id: 'platforms', name: 'Platforms', color: '#6366f1', angle: 0 },
  { id: 'techniques', name: 'Techniques', color: '#f97316', angle: 90 },
  { id: 'tools', name: 'Tools', color: '#06b6d4', angle: 180 },
  { id: 'languages', name: 'Languages', color: '#ec4899', angle: 270 },
];

export const RINGS: RingConfig[] = [
  { id: 'hold', name: 'Hold', color: '#ef4444', radius: 350 },
  { id: 'assess', name: 'Assess', color: '#f59e0b', radius: 275 },
  { id: 'trial', name: 'Trial', color: '#22d3ee', radius: 200 },
  { id: 'adopt', name: 'Adopt', color: '#22c55e', radius: 125 },
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
