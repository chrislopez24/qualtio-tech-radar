'use client';

import { useState, useCallback, useMemo, useDeferredValue } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from '@/components/Header';
import { Radar } from '@/components/Radar';
import { RadarSidebar } from '@/components/RadarSidebar';
import { WatchlistPanel } from '@/components/WatchlistPanel';
import { Legend } from '@/components/Legend';
import { DetailPanel } from '@/components/DetailPanel';
import { useRadarData } from '@/hooks/useRadarData';
import type { AITechnology, Technology, Quadrant, Ring, Trend } from '@/lib/types';
import { SPRING_SMOOTH } from '@/lib/animation-constants';
import { filterTechnologies, type RadarFilterState } from '@/lib/radar-filters';
import { getRadarContentState } from '@/lib/radar-view-state';

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <motion.div 
      className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={SPRING_SMOOTH}
    >
      <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center">
        <svg 
          className="w-8 h-8 text-muted-foreground" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="1.5"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <div className="text-center max-w-md">
        <h3 className="text-lg font-semibold mb-1">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </motion.div>
  );
}

export default function Home() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTech, setSelectedTech] = useState<Technology | AITechnology | null>(null);
  const [hoveredTechnologyId, setHoveredTechnologyId] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [filters, setFilters] = useState<RadarFilterState>({
    rings: [],
    quadrants: [],
    trends: [],
    minConfidence: null,
  });

  const aiData = useRadarData();
  const deferredSearchQuery = useDeferredValue(searchQuery);

  const handleSelect = useCallback((tech: Technology | AITechnology) => {
    setSelectedTech(tech);
    setPanelOpen(true);
  }, []);

  const handleClosePanel = useCallback(() => {
    setPanelOpen(false);
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
    setFilters({
      rings: [],
      quadrants: [],
      trends: [],
      minConfidence: null,
    });
  }, []);

  const technologies = useMemo(() => aiData?.technologies ?? [], [aiData]);
  const watchlist = useMemo(() => aiData?.watchlist ?? [], [aiData]);

  const visibleTechnologies = useMemo(
    () => filterTechnologies(technologies, deferredSearchQuery, filters),
    [technologies, deferredSearchQuery, filters],
  );

  const visibleWatchlist = useMemo(
    () => filterTechnologies(watchlist, deferredSearchQuery, filters),
    [watchlist, deferredSearchQuery, filters],
  );

  const contentState = getRadarContentState(technologies.length, visibleTechnologies.length);

  return (
    <div className="min-h-[100dvh] bg-background">
      <Header
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <main className="mx-auto max-w-[1600px] px-4 pb-4 pt-[100px] sm:px-6 lg:h-dvh lg:overflow-hidden lg:px-8">
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
              className="grid grid-cols-1 gap-4 lg:h-full lg:grid-cols-[minmax(0,1fr)_360px]"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={SPRING_SMOOTH}
            >
              <div className="min-w-0 lg:flex lg:h-full lg:flex-col">
                <div className="bento-card flex items-center justify-center p-3 sm:p-4 lg:h-full lg:min-h-0">
                    <Radar
                      technologies={visibleTechnologies}
                      allTechnologies={technologies}
                      selectedTech={selectedTech}
                      hoveredTechnologyId={hoveredTechnologyId}
                      onHoverTechnology={setHoveredTechnologyId}
                      onSelect={handleSelect}
                    />
                </div>

                <div className="lg:hidden">
                  <WatchlistPanel
                    watchlist={visibleWatchlist}
                    totalWatchlistCount={watchlist.length}
                    meta={aiData?.meta}
                    onSelectTechnology={handleSelect}
                  />
                </div>

                <div className="lg:hidden">
                  <Legend />
                </div>
              </div>

              <RadarSidebar
                visibleTechnologies={visibleTechnologies}
                totalTechnologies={technologies.length}
                selectedTechnologyId={selectedTech?.id ?? null}
                hoveredTechnologyId={hoveredTechnologyId}
                watchlist={visibleWatchlist}
                totalWatchlistCount={watchlist.length}
                meta={aiData?.meta}
                filters={filters}
                onToggleRing={toggleRing}
                onToggleQuadrant={toggleQuadrant}
                onToggleTrend={toggleTrend}
                onSetMinConfidence={setMinConfidence}
                onResetFilters={resetFilters}
                onHoverTechnology={setHoveredTechnologyId}
                onSelectTechnology={handleSelect}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <DetailPanel
        technology={selectedTech}
        open={panelOpen}
        onClose={handleClosePanel}
      />
    </div>
  );
}
