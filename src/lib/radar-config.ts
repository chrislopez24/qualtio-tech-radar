import type { QuadrantConfig, RingConfig, Quadrant, Ring } from './types';

export const RADAR_SIZE = 800;

// Colores Tech Noir - menos saturados para mejor legibilidad
export const QUADRANTS: QuadrantConfig[] = [
  { id: 'platforms', name: 'Platforms', color: '#3b82f6', angle: 0 },      // Azul más suave
  { id: 'techniques', name: 'Techniques', color: '#06b6d4', angle: 90 },   // Cyan
  { id: 'tools', name: 'Tools', color: '#10b981', angle: 180 },           // Esmeralda
  { id: 'languages', name: 'Languages', color: '#22c55e', angle: 270 },   // Verde
];

export const RINGS: RingConfig[] = [
  { id: 'hold', name: 'Hold', color: '#ef4444', radius: 350 },      // Rojo coral - detener
  { id: 'assess', name: 'Assess', color: '#f59e0b', radius: 275 },  // Ámbar - evaluar con cuidado
  { id: 'trial', name: 'Trial', color: '#06b6d4', radius: 200 },    // Cyan - probar
  { id: 'adopt', name: 'Adopt', color: '#22c55e', radius: 125 },    // Verde esmeralda - adoptar
];

export const getQuadrantById = (id: Quadrant): QuadrantConfig => {
  return QUADRANTS.find(q => q.id === id) || QUADRANTS[0];
};

export const getRingById = (id: Ring): RingConfig => {
  return RINGS.find(r => r.id === id) || RINGS[0];
};
