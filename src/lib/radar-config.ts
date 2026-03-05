import type { QuadrantConfig, RingConfig, Quadrant, Ring } from './types';

export const RADAR_SIZE = 800;

// Tech Noir palette
export const QUADRANTS: QuadrantConfig[] = [
  { id: 'platforms', name: 'Platforms', color: '#6366f1', angle: 0 },      // Indigo
  { id: 'techniques', name: 'Techniques', color: '#f59e0b', angle: 90 },   // Amber
  { id: 'tools', name: 'Tools', color: '#06b6d4', angle: 180 },            // Cyan
  { id: 'languages', name: 'Languages', color: '#ec4899', angle: 270 },    // Pink
];

export const RINGS: RingConfig[] = [
  { id: 'hold', name: 'Hold', color: '#ef4444', radius: 350 },
  { id: 'assess', name: 'Assess', color: '#f59e0b', radius: 275 },
  { id: 'trial', name: 'Trial', color: '#06b6d4', radius: 200 },
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
