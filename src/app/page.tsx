'use client';

import { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from '@/components/Header';
import { Radar } from '@/components/Radar';
import { RadarSidebar } from '@/components/RadarSidebar';
import { WatchlistPanel } from '@/components/WatchlistPanel';
import { Legend } from '@/components/Legend';
import { DetailPanel } from '@/components/DetailPanel';
import { useRadarData } from '@/hooks/useRadarData';
import type { AITechnology, AIRadarData, Technology, Quadrant, Ring, Trend } from '@/lib/types';
import { Spinner } from '@/components/ui/spinner';
import { WarningCircle } from '@phosphor-icons/react';
import { SPRING_SMOOTH } from '@/lib/animation-constants';
import { filterTechnologies, type RadarFilterState } from '@/lib/radar-filters';

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <Spinner className="w-8 h-8" />
      <div className="flex flex-col items-center gap-2">
        <p className="text-sm text-muted-foreground font-medium">
          Loading technologies...
        </p>
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40"
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.4, 1, 0.4],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: i * 0.2,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function ErrorState({ error }: { error: string }) {
  return (
    <motion.div 
      className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={SPRING_SMOOTH}
    >
      <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center">
        <WarningCircle className="w-8 h-8 text-destructive" weight="duotone" />
      </div>
      <div className="text-center max-w-md">
        <h3 className="text-lg font-semibold mb-1">Error loading data</h3>
        <p className="text-sm text-muted-foreground">{error}</p>
      </div>
    </motion.div>
  );
}

function EmptyState() {
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
        <h3 className="text-lg font-semibold mb-1">No technologies found</h3>
        <p className="text-sm text-muted-foreground">
          No technologies were found. Try reloading the page.
        </p>
      </div>
    </motion.div>
  );
}

export default function Home() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTech, setSelectedTech] = useState<Technology | AITechnology | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [filters, setFilters] = useState<RadarFilterState>({
    rings: [],
    quadrants: [],
    trends: [],
    minConfidence: null,
  });

  const { data, loading, error } = useRadarData('ai');

  const aiData = data as AIRadarData | null;

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
    () => filterTechnologies(technologies, searchQuery, filters),
    [technologies, searchQuery, filters],
  );

  const visibleWatchlist = useMemo(
    () => filterTechnologies(watchlist, searchQuery, filters),
    [watchlist, searchQuery, filters],
  );

  return (
    <div className="min-h-[100dvh] bg-background">
      <Header
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 pt-[100px]">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <LoadingState />
            </motion.div>
          ) : error ? (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <ErrorState error={error} />
            </motion.div>
          ) : technologies.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <EmptyState />
            </motion.div>
          ) : (
            <motion.div
              key="content"
              className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_360px]"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={SPRING_SMOOTH}
            >
              <div className="min-w-0">
                <div className="bento-card flex items-center justify-center p-3 sm:p-4">
                    <Radar
                      technologies={visibleTechnologies}
                      selectedTech={selectedTech}
                      searchQuery={searchQuery}
                      onSelect={handleSelect}
                    />
                </div>

                <WatchlistPanel
                  watchlist={visibleWatchlist}
                  meta={aiData?.meta}
                  onSelectTechnology={handleSelect}
                />

                <Legend />
              </div>

              <RadarSidebar
                visibleTechnologies={visibleTechnologies}
                totalTechnologies={technologies.length}
                selectedTechnologyId={selectedTech?.id ?? null}
                filters={filters}
                onToggleRing={toggleRing}
                onToggleQuadrant={toggleQuadrant}
                onToggleTrend={toggleTrend}
                onSetMinConfidence={setMinConfidence}
                onResetFilters={resetFilters}
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
