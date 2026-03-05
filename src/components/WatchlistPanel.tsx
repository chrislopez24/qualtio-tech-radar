'use client';

import { CheckCircle, WarningCircle } from '@phosphor-icons/react';
import type { AITechnology, AIRadarMeta } from '@/lib/types';
import { getQuadrantById, getRingById } from '@/lib/radar-config';

interface WatchlistPanelProps {
  watchlist: AITechnology[];
  meta?: AIRadarMeta;
  onSelectTechnology: (technology: AITechnology) => void;
}

function formatPercent(value?: number): string {
  if (typeof value !== 'number') return 'n/a';
  return `${Math.round(value * 100)}%`;
}

function getReviewStatus(nextReviewAt?: string): { label: string; tone: 'neutral' | 'warning' | 'danger' } {
  if (!nextReviewAt) {
    return { label: 'No review date', tone: 'neutral' };
  }

  const reviewDate = new Date(nextReviewAt);
  if (Number.isNaN(reviewDate.getTime())) {
    return { label: 'Invalid review date', tone: 'warning' };
  }

  const now = new Date();
  const diffMs = reviewDate.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) {
    return { label: `Overdue ${Math.abs(diffDays)}d`, tone: 'danger' };
  }

  if (diffDays <= 14) {
    return { label: `Due in ${diffDays}d`, tone: 'warning' };
  }

  return { label: `Due in ${diffDays}d`, tone: 'neutral' };
}

function reviewBadgeClass(tone: 'neutral' | 'warning' | 'danger'): string {
  if (tone === 'danger') {
    return 'border-rose-500/40 bg-rose-500/10 text-rose-300';
  }

  if (tone === 'warning') {
    return 'border-amber-500/40 bg-amber-500/10 text-amber-300';
  }

  return 'border-border/60 bg-background/70 text-muted-foreground';
}

function renderActionBadges(technology: AITechnology) {
  const reviewStatus = getReviewStatus(technology.nextReviewAt);

  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
      {technology.owner ? <span className="rounded border border-border/60 px-1.5 py-0.5">Owner: {technology.owner}</span> : null}
      {technology.nextStep ? <span className="rounded border border-border/60 px-1.5 py-0.5">Action: {technology.nextStep}</span> : null}
      <span className={`rounded border px-1.5 py-0.5 ${reviewBadgeClass(reviewStatus.tone)}`}>
        {reviewStatus.label}
      </span>
    </div>
  );
}

function getShadowStatusClass(status?: string): string {
  if (status === 'pass') return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300';
  if (status === 'fail') return 'border-rose-500/40 bg-rose-500/10 text-rose-300';
  return 'border-amber-500/40 bg-amber-500/10 text-amber-300';
}

export function WatchlistPanel({ watchlist, meta, onSelectTechnology }: WatchlistPanelProps) {
  const pipeline = meta?.pipeline;
  const shadow = meta?.shadowGate;

  return (
    <section className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="bento-card p-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">Watchlist</h3>
          <span className="text-xs text-muted-foreground">{watchlist.length} items</span>
        </div>
        {watchlist.length === 0 ? (
          <p className="text-sm text-muted-foreground">No watchlist entries in current run.</p>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-1">
            {watchlist.map((technology) => (
              <button
                key={technology.id}
                type="button"
                onClick={() => onSelectTechnology(technology)}
                className="rounded-xl border border-border/60 bg-background/70 px-3 py-2 text-left transition-colors hover:bg-muted/60"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium leading-tight">{technology.name}</p>
                  <span className="text-xs text-muted-foreground">{getRingById(technology.ring).name}</span>
                </div>

                <p className="mt-1 text-xs text-muted-foreground">{getQuadrantById(technology.quadrant).name}</p>

                {renderActionBadges(technology)}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="bento-card p-3">
        <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">Run Summary</h3>
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
          <span className="text-muted-foreground">Collected</span>
          <span className="font-mono">{pipeline?.collected ?? 'n/a'}</span>
          <span className="text-muted-foreground">Qualified</span>
          <span className="font-mono">{pipeline?.qualified ?? 'n/a'}</span>
          <span className="text-muted-foreground">Output</span>
          <span className="font-mono">{pipeline?.output ?? 'n/a'}</span>
          <span className="text-muted-foreground">Watchlist</span>
          <span className="font-mono">{pipeline?.watchlist ?? watchlist.length}</span>
          <span className="text-muted-foreground">Dropped desc.</span>
          <span className="font-mono">{pipeline?.droppedInvalidDescriptions ?? 0}</span>
        </div>

        {shadow && (
          <div className="mt-3 rounded-lg border border-border/60 bg-background/70 p-2.5">
            <div className="mb-2 flex items-center gap-2 text-xs">
              {shadow.status === 'pass' ? (
                <CheckCircle className="h-4 w-4 text-emerald-500" weight="fill" />
              ) : (
                <WarningCircle className="h-4 w-4 text-amber-500" weight="fill" />
              )}
              <span className="font-medium">Shadow gate {shadow.status ?? 'n/a'}</span>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
              <span className="text-muted-foreground">Core overlap</span>
              <span className="font-mono">{formatPercent(shadow.coreOverlap)}</span>
              <span className="text-muted-foreground">Leader coverage</span>
              <span className="font-mono">{formatPercent(shadow.leaderCoverage)}</span>
              <span className="text-muted-foreground">Watch recall</span>
              <span className="font-mono">{formatPercent(shadow.watchlistRecall)}</span>
              <span className="text-muted-foreground">LLM reduction</span>
              <span className="font-mono">{formatPercent(shadow.llmCallReduction)}</span>
              <span className="text-muted-foreground">Filtered</span>
              <span className="font-mono">{shadow.filteredCount ?? 0}</span>
            </div>

            <div className="mt-2 rounded border border-border/60 bg-background/60 p-2 text-[11px]">
              <p className="font-medium text-muted-foreground">What changed</p>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <span className={`rounded border px-1.5 py-0.5 font-semibold ${getShadowStatusClass(shadow.status)}`}>
                  {(shadow.status ?? 'warn').toUpperCase()}
                </span>
                <span className="rounded border border-border/60 px-1.5 py-0.5">Added: {shadow.addedCount ?? 0}</span>
                <span className="rounded border border-border/60 px-1.5 py-0.5">Filtered: {shadow.filteredCount ?? 0}</span>
              </div>
              <p className="mt-1 text-muted-foreground">Candidate transitions: {Object.keys(shadow.candidateChanges ?? {}).length}</p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
