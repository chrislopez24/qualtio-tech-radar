declare module '@/data/data.json' {
  import type { RadarData } from '@/lib/types';
  const value: RadarData;
  export default value;
}

declare module '@/data/data.ai.json' {
  import type { AIRadarData } from '@/lib/types';
  const value: AIRadarData;
  export default value;
}

declare module '@/data/data.ai.history.json' {
  const value: unknown;
  export default value;
}
