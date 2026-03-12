export interface RadarContentState {
  title: string;
  description: string;
}

export function getRadarContentState(
  totalTechnologies: number,
  visibleTechnologies: number,
): RadarContentState | null {
  if (totalTechnologies === 0) {
    return {
      title: 'No technologies found',
      description: 'No technologies were found. Try reloading the page.',
    };
  }

  if (visibleTechnologies === 0) {
    return {
      title: 'No matching technologies',
      description: 'No technologies match the current search or filters. Try clearing or adjusting them.',
    };
  }

  return null;
}
