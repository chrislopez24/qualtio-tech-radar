import { describe, expect, it } from 'vitest';
import aiData from '../data/data.ai.json';
import type { AITechnology } from './types';

function validateDecisionMetadataShape(technology: AITechnology): void {
  if (technology.whyNow !== undefined) {
    expect(typeof technology.whyNow).toBe('string');
  }

  if (technology.useCases !== undefined) {
    expect(Array.isArray(technology.useCases)).toBe(true);
    for (const useCase of technology.useCases) {
      expect(typeof useCase).toBe('string');
    }
  }

  if (technology.avoidWhen !== undefined) {
    expect(Array.isArray(technology.avoidWhen)).toBe(true);
    for (const avoid of technology.avoidWhen) {
      expect(typeof avoid).toBe('string');
    }
  }

  if (technology.maturityLevel !== undefined) {
    expect(['poc', 'pilot', 'production']).toContain(technology.maturityLevel);
  }

  if (technology.adoptionEffort !== undefined) {
    expect(['s', 'm', 'l']).toContain(technology.adoptionEffort);
  }

  if (technology.owner !== undefined) {
    expect(typeof technology.owner).toBe('string');
  }

  if (technology.nextStep !== undefined) {
    expect(typeof technology.nextStep).toBe('string');
  }

  if (technology.nextReviewAt !== undefined) {
    expect(typeof technology.nextReviewAt).toBe('string');
  }

  if (technology.evidence !== undefined) {
    expect(Array.isArray(technology.evidence)).toBe(true);
  }

  if (technology.alternatives !== undefined) {
    expect(Array.isArray(technology.alternatives)).toBe(true);
  }

  if (technology.risk !== undefined) {
    expect(typeof technology.risk).toBe('object');
    if (technology.risk?.security !== undefined) {
      expect(typeof technology.risk.security).toBe('string');
    }
    if (technology.risk?.lockIn !== undefined) {
      expect(typeof technology.risk.lockIn).toBe('string');
    }
    if (technology.risk?.talent !== undefined) {
      expect(typeof technology.risk.talent).toBe('string');
    }
    if (technology.risk?.cost !== undefined) {
      expect(typeof technology.risk.cost).toBe('string');
    }
  }
}

describe('radar data decision metadata schema', () => {
  it('accepts optional decision metadata fields when present', () => {
    const sample: AITechnology = {
      id: 'sample',
      name: 'Sample Tech',
      quadrant: 'tools',
      ring: 'trial',
      description: 'Sample description',
      trend: 'up',
      githubStars: 10,
      hnMentions: 2,
      confidence: 0.8,
      updatedAt: '2026-03-05T00:00:00.000Z',
      whyNow: 'Strong team demand for delivery speed.',
      useCases: ['Internal tooling', 'Prototyping'],
      avoidWhen: ['Strict compliance constraints'],
      maturityLevel: 'pilot',
      adoptionEffort: 'm',
      risk: {
        security: 'Needs stricter access controls.',
        lockIn: 'Moderate vendor coupling risk.',
      },
      owner: 'Platform Team',
      nextStep: 'Run pilot in one squad.',
      nextReviewAt: '2026-06-01',
      evidence: ['https://example.com/benchmark'],
      alternatives: ['Existing internal stack'],
    };

    expect(() => validateDecisionMetadataShape(sample)).not.toThrow();
  });

  it('keeps backward compatibility with existing items without metadata', () => {
    const minimal: AITechnology = {
      id: 'legacy',
      name: 'Legacy Tech',
      quadrant: 'platforms',
      ring: 'assess',
      description: 'Legacy entry with old shape.',
      trend: 'stable',
      confidence: 0.5,
      updatedAt: '2026-03-05T00:00:00.000Z',
    };

    expect(() => validateDecisionMetadataShape(minimal)).not.toThrow();
  });

  it('validates decision metadata shape for technologies in data.ai.json', () => {
    for (const technology of aiData.technologies) {
      expect(() => validateDecisionMetadataShape(technology as AITechnology)).not.toThrow();
    }
  });
});
