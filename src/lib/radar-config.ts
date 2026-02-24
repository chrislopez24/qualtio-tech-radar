import type { QuadrantConfig, RingConfig, Quadrant, Ring } from './types';

export const RADAR_SIZE = 800;

export const QUADRANTS: QuadrantConfig[] = [
  { id: 'platforms', name: 'Platforms', color: '#8b5cf6', angle: 0 },
  { id: 'techniques', name: 'Techniques', color: '#3b82f6', angle: 90 },
  { id: 'tools', name: 'Tools', color: '#06b6d4', angle: 180 },
  { id: 'languages', name: 'Languages', color: '#10b981', angle: 270 },
];

export const RINGS: RingConfig[] = [
  { id: 'hold', name: 'Hold', color: '#f43f5e', radius: 350 },
  { id: 'assess', name: 'Assess', color: '#8b5cf6', radius: 275 },
  { id: 'trial', name: 'Trial', color: '#3b82f6', radius: 200 },
  { id: 'adopt', name: 'Adopt', color: '#22c55e', radius: 125 },
];

export const getQuadrantById = (id: Quadrant): QuadrantConfig => {
  return QUADRANTS.find(q => q.id === id) || QUADRANTS[0];
};

export const getRingById = (id: Ring): RingConfig => {
  return RINGS.find(r => r.id === id) || RINGS[0];
};