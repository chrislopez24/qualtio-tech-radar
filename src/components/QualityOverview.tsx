'use client';

import type { PipelineSummary, QualitySnapshot } from '@/lib/types';

interface QualityOverviewProps {
  pipeline?: PipelineSummary;
}

function statusClass(status?: string): string {
  if (status === 'good') return 'text-emerald-300';
  if (status === 'bad') return 'text-rose-300';
  if (status === 'warn') return 'text-amber-300';
  return 'text-muted-foreground';
}

function renderSnapshot(label: string, snapshot?: QualitySnapshot) {
  if (!snapshot) return null;

  return (
    <div key={label} className="rounded border border-border/60 bg-background/60 px-2 py-1.5 text-[11px]">
      <div className="flex items-center justify-between gap-2">
        <span>{label}</span>
        <span className={`font-semibold ${statusClass(snapshot.status)}`}>{snapshot.status}</span>
      </div>
      <p className="mt-1 text-muted-foreground">
        {snapshot.count} items · avg {snapshot.avgMarketScore}
      </p>
    </div>
  );
}

export function QualityOverview({ pipeline }: QualityOverviewProps) {
  const ringQuality = pipeline?.ringQuality;
  const quadrantQuality = pipeline?.quadrantQuality;

  if (!ringQuality && !quadrantQuality) {
    return null;
  }

  return (
    <section className="rounded-xl border border-border/60 bg-background/90 p-2.5">
      <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Quality overview</h4>
      <div className="mt-2 grid gap-1.5">
        {renderSnapshot('Adopt', ringQuality?.adopt)}
        {renderSnapshot('Trial', ringQuality?.trial)}
        {renderSnapshot('Assess', ringQuality?.assess)}
        {renderSnapshot('Hold', ringQuality?.hold)}
        {renderSnapshot('Platforms', quadrantQuality?.platforms)}
        {renderSnapshot('Techniques', quadrantQuality?.techniques)}
        {renderSnapshot('Tools', quadrantQuality?.tools)}
        {renderSnapshot('Languages', quadrantQuality?.languages)}
      </div>
    </section>
  );
}
