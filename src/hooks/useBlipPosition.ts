import { useMemo } from 'react';
import type { Technology } from '@/lib/types';
import type { BlipPosition } from '@/lib/blip-position';
import { calculateBlipPositions } from '@/lib/blip-position';

export function useBlipPosition(technologies: Technology[]) {
  const positions = useMemo(() => calculateBlipPositions(technologies), [technologies]);

  const getPosition = (techId: string): BlipPosition | undefined => {
    return positions.get(techId);
  };

  return { getPosition, positions };
}
