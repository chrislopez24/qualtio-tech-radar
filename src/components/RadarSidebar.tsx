'use client';

import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, Funnel } from '@phosphor-icons/react';
import type { AIRadarMeta, AITechnology, Quadrant, Ring, Trend } from '@/lib/types';
import { QUADRANTS, RINGS } from '@/lib/radar-config';
import type { RadarFilterState } from '@/lib/radar-filters';
import { QualityOverview } from './QualityOverview';

type RingId = 'adopt' | 'trial' | 'assess' | 'hold';
type SidebarView = 'technologies' | 'watchlist' | 'guide';

const RING_ORDER: RingId[] = ['adopt', 'trial', 'assess', 'hold'];
const SIDEBAR_VIEWS: Array<{ id: SidebarView; label: string }> = [
  { id: 'technologies', label: 'Technologies' },
  { id: 'watchlist', label: 'Watchlist' },
  { id: 'guide', label: 'Guide' },
];

interface RadarSidebarProps {
  visibleTechnologies: AITechnology[];
  totalTechnologies: number;
  selectedTechnologyId: string | null;
  hoveredTechnologyId: string | null;
  watchlist?: AITechnology[];
  totalWatchlistCount?: number;
  meta?: AIRadarMeta;
  filters: RadarFilterState;
  onToggleRing: (ring: Ring) => void;
  onToggleQuadrant: (quadrant: Quadrant) => void;
  onToggleTrend: (trend: Trend) => void;
  onSetMinConfidence: (confidence: number | null) => void;
  onResetFilters: () => void;
  onHoverTechnology: (technologyId: string | null) => void;
  onSelectTechnology: (technology: AITechnology) => void;
}

export function RadarSidebar({
  visibleTechnologies,
  totalTechnologies,
  selectedTechnologyId,
  hoveredTechnologyId,
  watchlist = [],
  totalWatchlistCount,
  meta,
  filters,
  onToggleRing,
  onToggleQuadrant,
  onToggleTrend,
  onSetMinConfidence,
  onResetFilters,
  onHoverTechnology,
  onSelectTechnology,
}: RadarSidebarProps) {
  const [activeView, setActiveView] = useState<SidebarView>('technologies');
  const hiddenCount = Math.max(0, totalTechnologies - visibleTechnologies.length);
  const totalWatchlistItems = totalWatchlistCount ?? watchlist.length;
  const hasFilteredWatchlist = totalWatchlistItems > watchlist.length;

  const groupedByRing = useMemo(() => {
    const groups: Record<RingId, AITechnology[]> = {
      adopt: [],
      trial: [],
      assess: [],
      hold: [],
    };

    for (const technology of visibleTechnologies) {
      const ring = technology.ring as RingId;
      if (groups[ring]) {
        groups[ring].push(technology);
      }
    }

    for (const ring of RING_ORDER) {
      groups[ring].sort((a, b) => {
        const scoreA = a.marketScore ?? 0;
        const scoreB = b.marketScore ?? 0;
        return scoreB - scoreA || a.name.localeCompare(b.name);
      });
    }

    return groups;
  }, [visibleTechnologies]);

  const ringCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const ring of RINGS) counts.set(ring.id, 0);
    for (const technology of visibleTechnologies) {
      counts.set(technology.ring, (counts.get(technology.ring) ?? 0) + 1);
    }
    return counts;
  }, [visibleTechnologies]);

  const quadrantCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const quadrant of QUADRANTS) counts.set(quadrant.id, 0);
    for (const technology of visibleTechnologies) {
      counts.set(technology.quadrant, (counts.get(technology.quadrant) ?? 0) + 1);
    }
    return counts;
  }, [visibleTechnologies]);

  const trendCounts = useMemo(() => {
    const counts = new Map<Trend, number>([
      ['up', 0],
      ['stable', 0],
      ['new', 0],
      ['down', 0],
    ]);

    for (const technology of visibleTechnologies) {
      counts.set(technology.trend, (counts.get(technology.trend) ?? 0) + 1);
    }

    return counts;
  }, [visibleTechnologies]);

  const minConfidenceInput = filters.minConfidence === null ? '' : filters.minConfidence.toString();

  return (
    <aside className="bento-card flex h-auto min-h-0 flex-col overflow-hidden p-3 lg:h-full">
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-xl border border-border/60 bg-background/80 p-2">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Eye className="h-3.5 w-3.5" weight="duotone" />
            Visible
          </div>
          <p className="mt-0.5 text-xl font-semibold tracking-tight">{visibleTechnologies.length}</p>
        </div>
        <div className="rounded-xl border border-border/60 bg-background/80 p-2">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Funnel className="h-3.5 w-3.5" weight="duotone" />
            Filtered
          </div>
          <p className="mt-0.5 text-xl font-semibold tracking-tight">{hiddenCount}</p>
        </div>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-1.5 text-[11px]">
        {RINGS.map((ring) => (
          <div key={ring.id} className="flex items-center justify-between rounded-md border border-border/55 bg-background/70 px-2 py-1">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: ring.color }} />
              {ring.name}
            </span>
            <span className="font-mono text-muted-foreground">{ringCounts.get(ring.id) ?? 0}</span>
          </div>
        ))}
      </div>

      <div className="mt-1.5 grid grid-cols-2 gap-1.5 text-[11px]">
        {QUADRANTS.map((quadrant) => (
          <div key={quadrant.id} className="flex items-center justify-between rounded-md border border-border/55 bg-background/70 px-2 py-1">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: quadrant.color }} />
              {quadrant.name}
            </span>
            <span className="font-mono text-muted-foreground">{quadrantCounts.get(quadrant.id) ?? 0}</span>
          </div>
        ))}
      </div>

      <div className="mt-2 rounded-xl border border-border/60 bg-background/90 p-2">
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Filters</h4>
          {hiddenCount > 0 ? (
            <button
              type="button"
              onClick={onResetFilters}
              className="rounded-full border border-primary/40 bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-foreground transition-colors hover:bg-primary/15"
            >
              Reset {hiddenCount}
            </button>
          ) : (
            <button
              type="button"
              onClick={onResetFilters}
              className="text-[11px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              Reset
            </button>
          )}
        </div>

        <div className="space-y-2">
          <div>
            <p className="mb-1 text-[11px] font-medium text-muted-foreground">Ring</p>
            <div className="flex flex-wrap gap-1">
              {RINGS.map((ring) => {
                const active = filters.rings.includes(ring.id);
                return (
                  <button
                    key={ring.id}
                    type="button"
                    onClick={() => onToggleRing(ring.id)}
                    className={`rounded-md border px-1.5 py-0.5 text-[10px] transition-colors ${
                      active
                        ? 'border-primary/60 bg-primary/10 text-foreground'
                        : 'border-border/60 bg-background/70 text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {ring.name}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <p className="mb-1 text-[11px] font-medium text-muted-foreground">Quadrant</p>
            <div className="flex flex-wrap gap-1">
              {QUADRANTS.map((quadrant) => {
                const active = filters.quadrants.includes(quadrant.id);
                return (
                  <button
                    key={quadrant.id}
                    type="button"
                    onClick={() => onToggleQuadrant(quadrant.id)}
                    className={`rounded-md border px-1.5 py-0.5 text-[10px] transition-colors ${
                      active
                        ? 'border-primary/60 bg-primary/10 text-foreground'
                        : 'border-border/60 bg-background/70 text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {quadrant.name}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <p className="mb-1 text-[11px] font-medium text-muted-foreground">Trend</p>
            <div className="flex flex-wrap gap-1">
              {(['up', 'stable', 'new', 'down'] as Trend[]).map((trend) => {
                const active = filters.trends.includes(trend);
                return (
                  <button
                    key={trend}
                    type="button"
                    onClick={() => onToggleTrend(trend)}
                    className={`rounded-md border px-1.5 py-0.5 text-[10px] capitalize transition-colors ${
                      active
                        ? 'border-primary/60 bg-primary/10 text-foreground'
                        : 'border-border/60 bg-background/70 text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {trend} ({trendCounts.get(trend) ?? 0})
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label htmlFor="min-confidence" className="mb-1 block text-[11px] font-medium text-muted-foreground">
              Min confidence
            </label>
            <input
              id="min-confidence"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={minConfidenceInput}
              onChange={(event) => {
                const value = event.target.value;
                if (!value) {
                  onSetMinConfidence(null);
                  return;
                }

                const parsed = Number(value);
                if (!Number.isNaN(parsed)) {
                  onSetMinConfidence(Math.max(0, Math.min(1, parsed)));
                }
              }}
              className="h-8 w-full rounded-md border border-border/70 bg-background px-2 text-xs"
              placeholder="Any"
            />
          </div>
        </div>
      </div>

      <div className="mt-2 min-h-0 flex-1 overflow-hidden rounded-xl border border-border/60 bg-background/90 p-3">
        <div className="mb-2 flex items-center gap-1.5">
          {SIDEBAR_VIEWS.map((view) => {
                  const active = activeView === view.id;
                  const count = view.id === 'technologies'
                    ? visibleTechnologies.length
                    : view.id === 'watchlist'
                      ? watchlist.length
                      : undefined;
                  return (
                    <button
                      key={view.id}
                      type="button"
                      onClick={() => setActiveView(view.id)}
                      className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors ${
                        active
                          ? 'border-primary/70 bg-primary/12 text-foreground shadow-[0_0_0_1px_rgba(255,255,255,0.04)_inset]'
                          : 'border-border/60 bg-background/70 text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <span className="inline-flex items-center gap-1.5">
                        <span>{view.label}</span>
                        {typeof count === 'number' ? (
                          <span className={`rounded-full px-1.5 py-0.5 text-[10px] ${active ? 'bg-white/10 text-foreground' : 'bg-background/70 text-muted-foreground'}`}>
                            {count}
                          </span>
                        ) : null}
                      </span>
                    </button>
                  );
                })}
        </div>

        <div className="h-full overflow-y-auto pr-1">
          {activeView === 'technologies' ? (
            <>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-lg font-semibold tracking-tight">Technologies</h3>
                <span className="text-xs text-muted-foreground">Visible in radar</span>
              </div>
              {RING_ORDER.map((ringId) => {
                const ringItems = groupedByRing[ringId];
                if (!ringItems.length) return null;
                const ring = RINGS.find((value) => value.id === ringId)!;

                return (
                  <section key={ringId} className="mb-3">
                    <div className="mb-2 text-[12px] font-semibold uppercase tracking-[0.16em]" style={{ color: ring.color }}>
                      {ring.name}
                    </div>
                    <div className="space-y-1.5">
                      {ringItems.map((technology, index) => {
                        const isSelected = selectedTechnologyId === technology.id;
                        return (
                          <motion.button
                            key={technology.id}
                            type="button"
                            onClick={() => onSelectTechnology(technology)}
                        className={`flex w-full items-center gap-2 rounded-xl border px-2 py-1.5 text-left transition-colors ${
                          isSelected
                            ? 'border-primary/60 bg-primary/10'
                            : hoveredTechnologyId === technology.id
                              ? 'border-border/80 bg-muted/55'
                              : 'border-border/60 bg-background/70 hover:bg-muted/60'
                        }`}
                        onMouseEnter={() => onHoverTechnology(technology.id)}
                        onMouseLeave={() => onHoverTechnology(null)}
                        onFocus={() => onHoverTechnology(technology.id)}
                        onBlur={() => onHoverTechnology(null)}
                        whileTap={{ scale: 0.992 }}
                        transition={{ type: 'spring', stiffness: 420, damping: 28 }}
                      >
                        <span
                          className="inline-flex h-5 min-w-5 items-center justify-center rounded-full text-[9px] font-semibold text-white"
                          style={{ backgroundColor: ring.color }}
                        >
                          {index + 1}
                        </span>
                        <span className="truncate text-sm font-medium leading-none">{technology.name}</span>
                      </motion.button>
                        );
                      })}
                    </div>
                  </section>
                );
              })}
            </>
          ) : null}

          {activeView === 'watchlist' ? (
            <>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-lg font-semibold tracking-tight">Watchlist</h3>
                <span className="text-xs text-muted-foreground">
                  {hasFilteredWatchlist ? `${watchlist.length} of ${totalWatchlistItems}` : `${watchlist.length} items`}
                </span>
              </div>
              {watchlist.length === 0 ? (
                <p className="rounded-xl border border-border/60 bg-background/70 px-3 py-2 text-sm text-muted-foreground">
                  {hasFilteredWatchlist
                    ? 'No watchlist entries match current filters.'
                    : 'No watchlist entries in current run.'}
                </p>
              ) : (
                <div className="space-y-2">
                  {watchlist.map((technology) => (
                    <button
                      key={technology.id}
                      type="button"
                      onClick={() => onSelectTechnology(technology)}
                      className={`w-full rounded-xl border px-3 py-2 text-left transition-colors ${
                        hoveredTechnologyId === technology.id
                          ? 'border-border/80 bg-muted/55'
                          : 'border-border/60 bg-background/70 hover:bg-muted/60'
                      }`}
                      onMouseEnter={() => onHoverTechnology(technology.id)}
                      onMouseLeave={() => onHoverTechnology(null)}
                      onFocus={() => onHoverTechnology(technology.id)}
                      onBlur={() => onHoverTechnology(null)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-medium">{technology.name}</span>
                        <span className="text-[11px] text-muted-foreground">{technology.ring}</span>
                      </div>
                      <p className="mt-1 text-[11px] text-muted-foreground">{technology.quadrant}</p>
                    </button>
                  ))}
                </div>
              )}
            </>
          ) : null}

          {activeView === 'guide' ? (
            <div className="space-y-3">
              <section className="rounded-xl border border-border/60 bg-background/70 p-2.5">
                <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Run summary</h3>
                <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                  <span className="text-muted-foreground">Collected</span>
                  <span className="font-mono">{meta?.pipeline?.collected ?? 'n/a'}</span>
                  <span className="text-muted-foreground">Qualified</span>
                  <span className="font-mono">{meta?.pipeline?.qualified ?? 'n/a'}</span>
                  <span className="text-muted-foreground">Output</span>
                  <span className="font-mono">{meta?.pipeline?.output ?? 'n/a'}</span>
                  <span className="text-muted-foreground">Watchlist</span>
                  <span className="font-mono">{meta?.pipeline?.watchlist ?? totalWatchlistItems}</span>
                </div>
              </section>

              <QualityOverview pipeline={meta?.pipeline} />

              <section className="rounded-xl border border-border/60 bg-background/70 p-2.5">
                <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Guide</h3>
                <div className="mt-2 grid gap-1.5">
                  {RINGS.map((ring) => (
                    <div key={ring.id} className="flex items-center justify-between rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-[11px]">
                      <span className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: ring.color }} />
                        {ring.name}
                      </span>
                      <span className="font-mono text-muted-foreground">{ring.id}</span>
                    </div>
                  ))}
                  {QUADRANTS.map((quadrant) => (
                    <div key={quadrant.id} className="flex items-center justify-between rounded-lg border border-border/60 bg-background/60 px-2 py-1.5 text-[11px]">
                      <span className="flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: quadrant.color }} />
                        {quadrant.name}
                      </span>
                      <span className="font-mono text-muted-foreground">{quadrant.id.slice(0, 2).toUpperCase()}</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
