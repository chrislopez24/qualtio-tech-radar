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
}

export interface RadarData {
  updatedAt: string;
  technologies: Technology[];
}

export interface AIRadarData {
  updatedAt: string;
  technologies: AITechnology[];
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