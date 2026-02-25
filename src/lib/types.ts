export type Quadrant = 'platforms' | 'techniques' | 'tools' | 'languages';

export type Ring = 'adopt' | 'trial' | 'assess' | 'hold';

export type Mode = 'manual' | 'ai';

export type Trend = 'up' | 'down' | 'stable' | 'new';

export interface Technology {
  id: string;
  name: string;
  quadrant: Quadrant;
  ring: Ring;
  description: string;
  moved?: number;
}

export interface AITechnology extends Technology {
  trend: Trend;
  githubStars: number;
  hnMentions: number;
  confidence: number;
  updatedAt: string;
  marketScore?: number;
}

export interface PipelineSummary {
  collected?: number;
  normalized?: number;
  candidatesCore?: number;
  candidatesWatchlist?: number;
  candidatesBorderline?: number;
  classified?: number;
  qualified?: number;
  output?: number;
  watchlist?: number;
  droppedInvalidDescriptions?: number;
}

export interface ShadowGateSummary {
  status?: 'pass' | 'fail' | 'skip';
  coreOverlap?: number;
  leaderCoverage?: number;
  watchlistRecall?: number;
  llmCallReduction?: number;
  filteredCount?: number;
  addedCount?: number;
  filteredByRing?: Record<string, number>;
  filteredSample?: string[];
}

export interface AIRadarMeta {
  pipeline?: PipelineSummary;
  shadowGate?: ShadowGateSummary;
}

export interface RadarData {
  updatedAt: string;
  technologies: Technology[];
}

export interface AIRadarData {
  updatedAt: string;
  technologies: AITechnology[];
  watchlist?: AITechnology[];
  meta?: AIRadarMeta;
}

export interface QuadrantConfig {
  id: Quadrant;
  name: string;
  color: string;
  angle: number;
}

export interface RingConfig {
  id: Ring;
  name: string;
  color: string;
  radius: number;
}
