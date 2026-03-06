'use client';

import type { AIRadarData } from '@/lib/types';
import aiData from '@/data/data.ai.json';

export function useRadarData() {
  return aiData as AIRadarData;
}
