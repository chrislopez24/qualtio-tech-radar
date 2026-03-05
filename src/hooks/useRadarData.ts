'use client';

import { useMemo } from 'react';
import type { RadarData, AIRadarData, Mode } from '@/lib/types';
import manualData from '@/data/data.json';
import aiData from '@/data/data.ai.json';

export function useRadarData(mode: Mode) {
  const data = useMemo<RadarData | AIRadarData>(() => {
    if (mode === 'manual') {
      return manualData;
    }
    return aiData;
  }, [mode]);

  return { data, loading: false, error: null };
}
