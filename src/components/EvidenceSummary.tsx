'use client';

import type { AITechnology } from '@/lib/types';
import { SourceCoverageBadge } from './SourceCoverageBadge';

interface EvidenceSummaryProps {
  technology: AITechnology;
}

function formatFreshness(technology: AITechnology): string | null {
  const freshness = technology.sourceFreshness;
  if (!freshness) return null;
  if (freshness.freshestDays === null || freshness.stalestDays === null) return null;
  return `freshest ${freshness.freshestDays}d · stalest ${freshness.stalestDays}d`;
}

export function EvidenceSummary({ technology }: EvidenceSummaryProps) {
  const summary = technology.evidenceSummary;
  const freshness = formatFreshness(technology);

  if (!technology.whyThisRing && !summary && !technology.sourceCoverage && !freshness) {
    return null;
  }

  return (
    <section className="space-y-2 text-sm">
      {technology.whyThisRing ? (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Why this ring</h4>
          <p className="mt-1 text-muted-foreground">{technology.whyThisRing}</p>
        </div>
      ) : null}

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Source coverage</h4>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <SourceCoverageBadge
            coverage={technology.sourceCoverage}
            githubOnly={summary?.githubOnly}
          />
          {freshness ? <span className="text-xs text-muted-foreground">{freshness}</span> : null}
        </div>
      </div>

      {summary ? (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Evidence summary</h4>
          <p className="mt-1 text-muted-foreground">
            Sources: {summary.sources.join(', ') || 'n/a'}
          </p>
          <p className="mt-1 text-muted-foreground">
            Metrics: {summary.metrics.join(', ') || 'n/a'}
          </p>
        </div>
      ) : null}
    </section>
  );
}
