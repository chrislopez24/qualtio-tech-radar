'use client';

import { CheckCircle, WarningCircle } from '@phosphor-icons/react';
import type { AITechnology, AIRadarMeta } from '@/lib/types';

interface WatchlistPanelProps {
  watchlist: AITechnology[];
  meta?: AIRadarMeta;
  onSelectTechnology: (technology: AITechnology) => void;
}

function formatPercent(value?: number): string {
  if (typeof value !== 'number') return 'n/a';
  return `${Math.round(value * 100)}%`;
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
                className="flex items-center justify-between rounded-xl border border-border/60 bg-background/70 px-3 py-2 text-left transition-colors hover:bg-muted/60"
              >
                <div>
                  <p className="text-sm font-medium leading-tight">{technology.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{technology.quadrant}</p>
                </div>
                <span className="text-xs text-muted-foreground">{technology.ring}</span>
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
          </div>
        )}
      </div>
    </section>
  );
}
