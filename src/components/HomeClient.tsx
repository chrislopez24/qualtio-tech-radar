'use client';

import { useState, useCallback, useMemo, useDeferredValue, useEffect, startTransition } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from '@/components/Header';
import { Radar } from '@/components/Radar';
import { RadarSidebar } from '@/components/RadarSidebar';
import { DetailPanel } from '@/components/DetailPanel';
import type { AIRadarData, AITechnology, Technology, Quadrant, Ring, Trend } from '@/lib/types';
import { SPRING_SMOOTH } from '@/lib/animation-constants';
import { filterTechnologies, type RadarFilterState } from '@/lib/radar-filters';
import { getRadarContentState } from '@/lib/radar-view-state';
import { parseRadarUrlState, serializeRadarUrlState } from '@/lib/url-state';
import { QUADRANTS, RINGS } from '@/lib/radar-config';

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

type Preset = 'strong' | 'rising' | 'review';
type MobileView = 'radar' | 'explore' | 'watchlist' | 'quality';

const MOBILE_VIEWS: Array<{ id: MobileView; label: string }> = [
  { id: 'radar', label: 'Radar' },
  { id: 'explore', label: 'Explore' },
  { id: 'watchlist', label: 'Watchlist' },
  { id: 'quality', label: 'Quality' },
];

const QUICK_PRESETS: Array<{ id: Preset; label: string; meta: string }> = [
  { id: 'strong', label: 'Strong signals', meta: 'Adopt + Trial' },
  { id: 'rising', label: 'Rising', meta: 'Up or new' },
  { id: 'review', label: 'Needs review', meta: 'Assess + Hold' },
];

export function HomeClient({ initialData }: HomeClientProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTech, setSelectedTech] = useState<Technology | AITechnology | null>(null);
  const [selectedAnchor, setSelectedAnchor] = useState<{ x: number; y: number } | null>(null);
  const [hoveredTechnologyId, setHoveredTechnologyId] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [filters, setFilters] = useState<RadarFilterState>(DEFAULT_FILTERS);
  const [activePreset, setActivePreset] = useState<Preset | null>(null);
  const [mobileView, setMobileView] = useState<MobileView>('radar');
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
  }, []);

  const handlePanelExited = useCallback(() => {
    setSelectedTech(null);
    setSelectedAnchor(null);
  }, []);

  const toggleRing = useCallback((ring: Ring) => {
    setActivePreset(null);
    setFilters((prev) => ({
      ...prev,
      rings: prev.rings.includes(ring)
        ? prev.rings.filter((value) => value !== ring)
        : [...prev.rings, ring],
    }));
  }, []);

  const toggleQuadrant = useCallback((quadrant: Quadrant) => {
    setActivePreset(null);
    setFilters((prev) => ({
      ...prev,
      quadrants: prev.quadrants.includes(quadrant)
        ? prev.quadrants.filter((value) => value !== quadrant)
        : [...prev.quadrants, quadrant],
    }));
  }, []);

  const toggleTrend = useCallback((trend: Trend) => {
    setActivePreset(null);
    setFilters((prev) => ({
      ...prev,
      trends: prev.trends.includes(trend)
        ? prev.trends.filter((value) => value !== trend)
        : [...prev.trends, trend],
    }));
  }, []);

  const setMinConfidence = useCallback((value: number | null) => {
    setActivePreset(null);
    setFilters((prev) => ({ ...prev, minConfidence: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    setActivePreset(null);
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

  const applyPreset = useCallback((preset: Preset) => {
    startTransition(() => {
      setActivePreset(preset);
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

      <main className="dashboard-main mx-auto max-w-[1760px] px-3 pb-6 pt-[136px] sm:px-5 md:pt-[88px] lg:px-6">
        <section className="workbench-strip mb-3 lg:mb-2">
          <div className="min-w-0">
            <p className="section-kicker">Editorial radar</p>
            <h1 className="mt-1 text-balance text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
              Market signals, filtered into adoption decisions.
            </h1>
          </div>

          <div className="hidden min-w-0 items-center gap-1 lg:flex" aria-label="Quick presets">
            {QUICK_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => applyPreset(preset.id)}
                aria-pressed={activePreset === preset.id}
                className={`command-chip min-w-fit ${activePreset === preset.id ? 'command-chip-active' : ''}`}
              >
                <span>{preset.label}</span>
                <small>{preset.meta}</small>
              </button>
            ))}
            <button
              type="button"
              onClick={resetFilters}
              className="command-chip justify-center"
            >
              <span>Reset</span>
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:justify-end">
            <div className="metric-tile">
              <span>Visible</span>
              <strong>{visibleTechnologies.length}</strong>
            </div>
            <div className="metric-tile">
              <span>Watchlist</span>
              <strong>{visibleWatchlist.length}</strong>
            </div>
            <div className="metric-tile hidden sm:block">
              <span>Adopt</span>
              <strong>{ringCounts.get('adopt') ?? 0}</strong>
            </div>
            <div className="metric-tile hidden sm:block">
              <span>Tools</span>
              <strong>{quadrantCounts.get('tools') ?? 0}</strong>
            </div>
          </div>
        </section>

        <section className="mb-3 flex flex-col gap-2 rounded-2xl border border-border/60 bg-bg-secondary/70 p-2 sm:flex-row sm:items-center sm:justify-between lg:hidden">
          <div className="flex min-w-0 gap-1 overflow-x-auto no-scrollbar" aria-label="Quick presets">
            {QUICK_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => applyPreset(preset.id)}
                aria-pressed={activePreset === preset.id}
                className={`command-chip min-w-fit ${activePreset === preset.id ? 'command-chip-active' : ''}`}
              >
                <span>{preset.label}</span>
                <small>{preset.meta}</small>
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={resetFilters}
            className="command-chip justify-center sm:min-w-[92px]"
          >
            <span>Reset</span>
          </button>
        </section>

        <nav className="mb-3 grid grid-cols-4 gap-1 rounded-2xl border border-border/60 bg-bg-secondary/80 p-1 lg:hidden" aria-label="Mobile radar views">
          {MOBILE_VIEWS.map((view) => (
            <button
              key={view.id}
              type="button"
              onClick={() => setMobileView(view.id)}
              aria-pressed={mobileView === view.id}
              className={`rounded-xl px-2 py-2 text-xs font-semibold transition-colors ${
                mobileView === view.id
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'
              }`}
            >
              {view.label}
            </button>
          ))}
        </nav>

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
              className="dashboard-content grid grid-cols-1 gap-3"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={SPRING_SMOOTH}
            >
              <div className={`min-w-0 lg:flex lg:min-h-0 lg:flex-col ${mobileView !== 'radar' ? 'hidden lg:flex' : ''}`}>
                <div className="radar-stage relative flex items-center justify-center lg:h-full lg:min-h-0">
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
                    onExited={handlePanelExited}
                  />
                </div>
              </div>

              <div className={`dashboard-sidebar ${mobileView === 'radar' ? 'hidden lg:block' : ''}`}>
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
                  forcedView={
                    mobileView === 'watchlist'
                      ? 'watchlist'
                      : mobileView === 'quality'
                        ? 'guide'
                        : mobileView === 'explore'
                          ? 'technologies'
                          : undefined
                  }
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
