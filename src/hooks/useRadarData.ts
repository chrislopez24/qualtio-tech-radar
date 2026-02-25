'use client';

import { useState, useEffect } from 'react';
import type { RadarData, AIRadarData, Mode } from '@/lib/types';
import manualData from '@/data/data.json';
import aiData from '@/data/data.ai.json';

export function useRadarData(mode: Mode) {
  const [data, setData] = useState<RadarData | AIRadarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);

      try {
        if (mode === 'manual') {
          setData(manualData as RadarData);
        } else {
          if (aiData) {
            setData(aiData as unknown as AIRadarData);
          } else {
            setData(manualData as RadarData);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
        setData(manualData as RadarData);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [mode]);

  return { data, loading, error };
}
