export type Quadrant = 'platforms' | 'techniques' | 'tools' | 'languages';

export type Ring = 'adopt' | 'trial' | 'assess' | 'hold';

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

export interface EvidenceRecordView {
  source: string;
  metric: string;
  subjectId: string;
  rawValue: unknown;
  normalizedValue: number;
  observedAt: string;
  freshnessDays: number;
}

export interface EvidenceSummary {
  sources: string[];
  metrics: string[];
  hasExternalAdoption: boolean;
  githubOnly: boolean;
}

export interface SourceFreshness {
  freshestDays: number | null;
  stalestDays: number | null;
}

export interface QualitySnapshot {
  count: number;
  avgMarketScore: number;
  githubOnlyRatio: number;
  resourceLikeCount: number;
  editoriallyWeakCount: number;
  topSuspicious: Array<{
    id: string;
    name: string;
    marketScore: number;
    reasons: string[];
  }>;
  status: 'good' | 'warn' | 'bad' | 'missing';
}

export interface AITechnology extends Technology {
  trend: Trend;
  sourceSummary?: string;
  signalFreshness?: string;
  sourceCoverage?: number;
  sourceFreshness?: SourceFreshness;
  evidenceSummary?: EvidenceSummary;
  whyThisRing?: string;
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
  evidence?: Array<string | EvidenceRecordView>;
  alternatives?: string[];
  canonicalId?: string;
  entityType?: string;
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
  repairedDescriptions?: number;
  rejectedByStage?: {
    insufficientSources?: number;
    qualityGate?: number;
    aiFilter?: number;
  };
  ringDistribution?: Partial<Record<Ring, number>>;
  topAdded?: Array<{
    id: string;
    name: string;
    ring: Ring;
    marketScore: number;
  }>;
  topDropped?: Array<{
    id: string;
    name: string;
    ring: Ring;
    marketScore: number;
  }>;
  ringQuality?: Partial<Record<Ring, QualitySnapshot>>;
  quadrantQuality?: Partial<Record<Quadrant, QualitySnapshot>>;
  quadrantRingQuality?: Partial<Record<Quadrant, Partial<Record<Ring, QualitySnapshot>>>>;
}

export interface ShadowGateSummary {
  status?: 'pass' | 'warn' | 'fail' | 'skip';
  coreOverlap?: number;
  leaderCoverage?: number;
  watchlistRecall?: number;
  llmCallReduction?: number;
  filteredCount?: number;
  addedCount?: number;
  filteredByRing?: Record<string, number>;
  filteredSample?: string[];
  quadrantsMissingSourceCoverage?: string[];
  nextAction?: string | null;
  leaderTransitionSummary?: {
    candidateCount: number;
    promotedCount: number;
  };
  leaderState?: {
    stable_leaders?: string[];
    stableLeaders?: string[];
    candidate_changes?: Record<string, {
      leader_id: string;
      change_type: 'added' | 'removed';
      consecutive_count: number;
      first_seen_run?: string;
      last_seen_run?: string;
    }>;
    candidateChanges?: Record<string, {
      leaderId: string;
      changeType: 'added' | 'removed';
      consecutiveCount: number;
      firstSeenRun?: string;
      lastSeenRun?: string;
    }>;
    promoted_changes?: Array<{
      leader_id: string;
      change_type: 'added' | 'removed';
    }>;
    promotedChanges?: Array<{
      leaderId: string;
      changeType: 'added' | 'removed';
    }>;
    lastRunId?: string;
    promotionRuns?: number;
  };
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
