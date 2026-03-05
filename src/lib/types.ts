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

export type MaturityLevel = 'poc' | 'pilot' | 'production';

export type AdoptionEffort = 's' | 'm' | 'l';

export interface DecisionRisk {
  security?: string;
  lockIn?: string;
  talent?: string;
  cost?: string;
}

export interface AITechnology extends Technology {
  trend: Trend;
  sourceSummary?: string;
  signalFreshness?: string;
  githubStars?: number;
  hnMentions?: number;
  stars?: number;
  signals?: {
    ghMomentum?: number;
    ghPopularity?: number;
    hnHeat?: number;
  };
  confidence: number;
  updatedAt: string;
  marketScore?: number;
  whyNow?: string;
  useCases?: string[];
  avoidWhen?: string[];
  maturityLevel?: MaturityLevel;
  adoptionEffort?: AdoptionEffort;
  risk?: DecisionRisk;
  owner?: string;
  nextStep?: string;
  nextReviewAt?: string;
  evidence?: string[];
  alternatives?: string[];
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
  candidateChanges?: Record<string, {
    leaderId: string;
    changeType: 'added' | 'removed';
    consecutiveCount: number;
  }>;
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
