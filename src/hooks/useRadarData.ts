'use client';

import type { AIRadarData } from '@/lib/types';
import aiData from '@/data/data.ai.json';

export function useRadarData() {
  const data = aiData as AIRadarData;

  return {
    ...data,
    technologies: data.technologies ?? [],
    watchlist: data.watchlist ?? [],
    meta: data.meta ?? {},
  } satisfies AIRadarData;
}
