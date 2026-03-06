import { useMemo, useCallback } from 'react';
import type { Technology } from '@/lib/types';
import type { BlipPosition } from '@/lib/blip-position';
import { calculateVisibleBlipPositions } from '@/lib/blip-position';

export function useBlipPosition(
  technologies: Technology[],
  layoutTechnologies: Technology[] = technologies,
) {
  const positions = useMemo(
    () => calculateVisibleBlipPositions(technologies, layoutTechnologies),
    [technologies, layoutTechnologies],
  );

  const getPosition = useCallback(
    (techId: string): BlipPosition | undefined => {
      return positions.get(techId);
    },
    [positions],
  );

  return { getPosition, positions };
}
