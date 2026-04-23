'use client';

import { useState, useCallback, useMemo, useDeferredValue, useEffect, startTransition } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from '@/components/Header';
import { Radar } from '@/components/Radar';
import { RadarSidebar } from '@/components/RadarSidebar';
import { WatchlistPanel } from '@/components/WatchlistPanel';
import { Legend } from '@/components/Legend';
import { DetailPanel } from '@/components/DetailPanel';
import type { AIRadarData, AITechnology, Technology, Quadrant, Ring, Trend } from '@/lib/types';
import { SPRING_SMOOTH } from '@/lib/animation-constants';
import { filterTechnologies, type RadarFilterState } from '@/lib/radar-filters';
import { getRadarContentState } from '@/lib/radar-view-state';
import { parseRadarUrlState, serializeRadarUrlState } from '@/lib/url-state';

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <motion.div
      className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={SPRING_SMOOTH}
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
        <svg
          className="h-8 w-8 text-muted-foreground"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <div className="max-w-md text-center">
        <h3 className="mb-1 text-lg font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </motion.div>
  );
}

interface HomeClientProps {
  initialData: AIRadarData;
}

const DEFAULT_FILTERS: RadarFilterState = {
  rings: [],
  quadrants: [],
  trends: [],
  minConfidence: null,
};

export function HomeClient({ initialData }: HomeClientProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTech, setSelectedTech] = useState<Technology | AITechnology | null>(null);
  const [selectedAnchor, setSelectedAnchor] = useState<{ x: number; y: number } | null>(null);
  const [hoveredTechnologyId, setHoveredTechnologyId] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [filters, setFilters] = useState<RadarFilterState>(DEFAULT_FILTERS);
  const deferredSearchQuery = useDeferredValue(searchQuery);

  useEffect(() => {
    const applyFromLocation = () => {
      const state = parseRadarUrlState(new URLSearchParams(window.location.search));
      startTransition(() => {
        setSearchQuery(state.searchQuery);
        setFilters(state.filters);
      });
    };

    applyFromLocation();
    window.addEventListener('popstate', applyFromLocation);
    return () => window.removeEventListener('popstate', applyFromLocation);
  }, []);

  useEffect(() => {
    const params = serializeRadarUrlState({ searchQuery, filters });
    const nextSearch = params.toString();
    const currentSearch = window.location.search.replace(/^\?/, '');

    if (nextSearch === currentSearch) {
      return;
    }

    const nextUrl = nextSearch ? `${window.location.pathname}?${nextSearch}` : window.location.pathname;
    window.history.replaceState(null, '', nextUrl);
  }, [searchQuery, filters]);

  const handleSelect = useCallback((tech: Technology | AITechnology, anchor?: { x: number; y: number }) => {
    setSelectedTech(tech);
    setSelectedAnchor(anchor ?? null);
    setPanelOpen(true);
  }, []);

  const handleClosePanel = useCallback(() => {
    setPanelOpen(false);
    setSelectedTech(null);
    setSelectedAnchor(null);
  }, []);

  const toggleRing = useCallback((ring: Ring) => {
    setFilters((prev) => ({
      ...prev,
      rings: prev.rings.includes(ring)
        ? prev.rings.filter((value) => value !== ring)
        : [...prev.rings, ring],
    }));
  }, []);

  const toggleQuadrant = useCallback((quadrant: Quadrant) => {
    setFilters((prev) => ({
      ...prev,
      quadrants: prev.quadrants.includes(quadrant)
        ? prev.quadrants.filter((value) => value !== quadrant)
        : [...prev.quadrants, quadrant],
    }));
  }, []);

  const toggleTrend = useCallback((trend: Trend) => {
    setFilters((prev) => ({
      ...prev,
      trends: prev.trends.includes(trend)
        ? prev.trends.filter((value) => value !== trend)
        : [...prev.trends, trend],
    }));
  }, []);

  const setMinConfidence = useCallback((value: number | null) => {
    setFilters((prev) => ({ ...prev, minConfidence: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  const technologies = useMemo(() => initialData.technologies ?? [], [initialData]);
  const watchlist = useMemo(() => initialData.watchlist ?? [], [initialData]);

  const visibleTechnologies = useMemo(
    () => filterTechnologies(technologies, deferredSearchQuery, filters),
    [technologies, deferredSearchQuery, filters],
  );

  const visibleWatchlist = useMemo(
    () => filterTechnologies(watchlist, deferredSearchQuery, filters),
    [watchlist, deferredSearchQuery, filters],
  );

  const contentState = getRadarContentState(technologies.length, visibleTechnologies.length);

  const applyPreset = useCallback((preset: 'strong' | 'rising' | 'review') => {
    startTransition(() => {
      setSearchQuery('');
      if (preset === 'strong') {
        setFilters({ rings: ['adopt', 'trial'], quadrants: [], trends: [], minConfidence: 0.7 });
        return;
      }
      if (preset === 'rising') {
        setFilters({ rings: [], quadrants: [], trends: ['up', 'new'], minConfidence: 0.6 });
        return;
      }
      setFilters({ rings: ['assess', 'hold'], quadrants: [], trends: [], minConfidence: null });
    });
  }, []);

  return (
    <div className="min-h-[100dvh] bg-background">
      <Header searchQuery={searchQuery} onSearchChange={setSearchQuery} />

      <main className="mx-auto max-w-[1840px] px-4 pb-6 pt-[100px] sm:px-6 lg:px-8">
        <section className="mb-4 grid gap-3 lg:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.85fr)]">
          <div className="bento-card p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-cyan">How to read this radar</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Read signal strength before chasing novelty.</h2>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Discovery comes from GitHub and Hacker News. Strong rings are then validated with deps.dev and OSV so momentum alone does not over-promote risky or weakly corroborated technologies.
            </p>
          </div>

          <div className="bento-card p-4">
            <p className="text-[11px] font-mono uppercase tracking-[0.28em] text-muted-foreground">Quick presets</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-1">
              <button type="button" onClick={() => applyPreset('strong')} className="rounded-xl border border-border/60 bg-background/70 px-3 py-2 text-left transition-colors hover:bg-muted/60">
                <p className="text-sm font-medium">Strong signals</p>
                <p className="text-xs text-muted-foreground">Adopt + Trial with high confidence.</p>
              </button>
              <button type="button" onClick={() => applyPreset('rising')} className="rounded-xl border border-border/60 bg-background/70 px-3 py-2 text-left transition-colors hover:bg-muted/60">
                <p className="text-sm font-medium">Rising bets</p>
                <p className="text-xs text-muted-foreground">Up or new technologies worth shortlisting.</p>
              </button>
              <button type="button" onClick={() => applyPreset('review')} className="rounded-xl border border-border/60 bg-background/70 px-3 py-2 text-left transition-colors hover:bg-muted/60">
                <p className="text-sm font-medium">Needs review</p>
                <p className="text-xs text-muted-foreground">Assess and Hold items that need clearer calls.</p>
              </button>
            </div>
          </div>
        </section>

        <AnimatePresence mode="wait">
          {contentState ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <EmptyState title={contentState.title} description={contentState.description} />
            </motion.div>
          ) : (
            <motion.div
              key="content"
              className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.35fr)_380px]"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={SPRING_SMOOTH}
            >
              <div className="min-w-0 lg:flex lg:flex-col">
                <div className="bento-card relative flex items-center justify-center p-3 sm:p-4">
                  <Radar
                    technologies={visibleTechnologies}
                    allTechnologies={technologies}
                    selectedTech={selectedTech}
                    hoveredTechnologyId={hoveredTechnologyId}
                    onHoverTechnology={setHoveredTechnologyId}
                    onSelect={handleSelect}
                  />
                  <DetailPanel
                    technology={selectedTech}
                    open={panelOpen}
                    anchor={selectedAnchor}
                    onClose={handleClosePanel}
                  />
                </div>

                <div className="lg:hidden">
                  <WatchlistPanel
                    watchlist={visibleWatchlist}
                    totalWatchlistCount={watchlist.length}
                    meta={initialData.meta}
                    referenceDate={initialData.updatedAt}
                    onSelectTechnology={handleSelect}
                  />
                </div>

                <div className="lg:hidden">
                  <Legend />
                </div>
              </div>

              <div className="lg:sticky lg:top-[100px] lg:max-h-[calc(100dvh-116px)]">
                <RadarSidebar
                  visibleTechnologies={visibleTechnologies}
                  totalTechnologies={technologies.length}
                  selectedTechnologyId={selectedTech?.id ?? null}
                  hoveredTechnologyId={hoveredTechnologyId}
                  watchlist={visibleWatchlist}
                  totalWatchlistCount={watchlist.length}
                  meta={initialData.meta}
                  filters={filters}
                  onToggleRing={toggleRing}
                  onToggleQuadrant={toggleQuadrant}
                  onToggleTrend={toggleTrend}
                  onSetMinConfidence={setMinConfidence}
                  onResetFilters={resetFilters}
                  onHoverTechnology={setHoveredTechnologyId}
                  onSelectTechnology={handleSelect}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
