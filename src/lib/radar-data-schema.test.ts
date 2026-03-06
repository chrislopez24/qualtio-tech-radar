import { describe, expect, it } from 'vitest';
import aiData from '../data/data.ai.json';
import type { AITechnology, ShadowGateSummary } from './types';

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

function validateShadowGateSummaryShape(shadowGate: ShadowGateSummary): void {
  if (shadowGate.status !== undefined) {
    expect(['pass', 'warn', 'fail', 'skip']).toContain(shadowGate.status);
  }

  if (shadowGate.nextAction !== undefined) {
    if (shadowGate.nextAction !== null) {
      expect(typeof shadowGate.nextAction).toBe('string');
    }
  }

  if (shadowGate.filteredCount !== undefined) {
    expect(typeof shadowGate.filteredCount).toBe('number');
  }

  if (shadowGate.addedCount !== undefined) {
    expect(typeof shadowGate.addedCount).toBe('number');
  }

  if (shadowGate.filteredSample !== undefined) {
    expect(Array.isArray(shadowGate.filteredSample)).toBe(true);
    for (const sample of shadowGate.filteredSample) {
      expect(typeof sample).toBe('string');
    }
  }

  if (shadowGate.leaderState !== undefined) {
    expect(shadowGate.leaderState).not.toBeNull();
    expect(typeof shadowGate.leaderState).toBe('object');
    expect(Array.isArray(shadowGate.leaderState)).toBe(false);

    if (shadowGate.leaderState?.stable_leaders !== undefined) {
      expect(Array.isArray(shadowGate.leaderState.stable_leaders)).toBe(true);
      for (const leaderId of shadowGate.leaderState.stable_leaders) {
        expect(typeof leaderId).toBe('string');
      }
    }

    if (shadowGate.leaderState?.candidate_changes !== undefined) {
      expect(shadowGate.leaderState.candidate_changes).not.toBeNull();
      expect(typeof shadowGate.leaderState.candidate_changes).toBe('object');
      expect(Array.isArray(shadowGate.leaderState.candidate_changes)).toBe(false);

      for (const [changeKey, change] of Object.entries(shadowGate.leaderState.candidate_changes)) {
        expect(typeof changeKey).toBe('string');
        expect(change).not.toBeNull();
        expect(typeof change).toBe('object');
        expect(Array.isArray(change)).toBe(false);
        expect(change).toHaveProperty('leader_id');
        expect(change).toHaveProperty('change_type');
        expect(change).toHaveProperty('consecutive_count');

        const typedChange = change as {
          leader_id?: unknown;
          change_type?: unknown;
          consecutive_count?: unknown;
        };

        expect(typeof typedChange.leader_id).toBe('string');
        expect(['added', 'removed']).toContain(typedChange.change_type);
        expect(typeof typedChange.consecutive_count).toBe('number');
      }
    }

    if (shadowGate.leaderState?.promoted_changes !== undefined) {
      expect(Array.isArray(shadowGate.leaderState.promoted_changes)).toBe(true);
      for (const promotedChange of shadowGate.leaderState.promoted_changes) {
        expect(promotedChange).not.toBeNull();
        expect(typeof promotedChange).toBe('object');
        expect(promotedChange).toHaveProperty('leader_id');
        expect(promotedChange).toHaveProperty('change_type');

        const typedPromotedChange = promotedChange as {
          leader_id?: unknown;
          change_type?: unknown;
        };

        expect(typeof typedPromotedChange.leader_id).toBe('string');
        expect(['added', 'removed']).toContain(typedPromotedChange.change_type);
      }
    }
  }

  if (shadowGate.candidateChanges !== undefined) {
    expect(shadowGate.candidateChanges).not.toBeNull();
    expect(typeof shadowGate.candidateChanges).toBe('object');
    expect(Array.isArray(shadowGate.candidateChanges)).toBe(false);

    for (const [changeKey, change] of Object.entries(shadowGate.candidateChanges)) {
      expect(typeof changeKey).toBe('string');
      expect(change).not.toBeNull();
      expect(typeof change).toBe('object');
      expect(Array.isArray(change)).toBe(false);
      expect(change).toHaveProperty('leaderId');
      expect(change).toHaveProperty('changeType');
      expect(change).toHaveProperty('consecutiveCount');

      const typedChange = change as {
        leaderId?: unknown;
        changeType?: unknown;
        consecutiveCount?: unknown;
      };

      expect(typeof typedChange.leaderId).toBe('string');
      expect(['added', 'removed']).toContain(typedChange.changeType);
      expect(typeof typedChange.consecutiveCount).toBe('number');
    }
  }

  if (shadowGate.leaderTransitionSummary !== undefined) {
    expect(shadowGate.leaderTransitionSummary).not.toBeNull();
    expect(typeof shadowGate.leaderTransitionSummary).toBe('object');
    expect(Array.isArray(shadowGate.leaderTransitionSummary)).toBe(false);
    expect(typeof shadowGate.leaderTransitionSummary.candidateCount).toBe('number');
    expect(typeof shadowGate.leaderTransitionSummary.promotedCount).toBe('number');
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

describe('radar data shadow gate schema', () => {
  it('accepts optional what-changed fields when present', () => {
    const sample: ShadowGateSummary = {
      status: 'warn',
      nextAction: 'Hold rollout until leader transitions stabilize.',
      filteredCount: 2,
      addedCount: 1,
      leaderTransitionSummary: {
        candidateCount: 1,
        promotedCount: 0,
      },
      filteredSample: ['legacy-js-framework'],
      leaderState: {
        stable_leaders: ['react', 'kubernetes'],
        candidate_changes: {
          'new-runtime:added': {
            leader_id: 'new-runtime',
            change_type: 'added',
            consecutive_count: 1,
          },
        },
      },
      candidateChanges: {
        'new-runtime:added': {
          leaderId: 'new-runtime',
          changeType: 'added',
          consecutiveCount: 1,
        },
      },
    };

    expect(() => validateShadowGateSummaryShape(sample)).not.toThrow();
  });

  it('keeps backward compatibility when shadow gate only has status', () => {
    const minimal: ShadowGateSummary = {
      status: 'skip',
    };

    expect(() => validateShadowGateSummaryShape(minimal)).not.toThrow();
  });

  it('validates shadow gate shape for data.ai.json when present', () => {
    const shadowGate = (aiData as { meta?: { shadowGate?: ShadowGateSummary } }).meta?.shadowGate;
    if (shadowGate !== undefined) {
      expect(() => validateShadowGateSummaryShape(shadowGate)).not.toThrow();
    }
  });

});
