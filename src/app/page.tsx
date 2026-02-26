'use client';

import { useState, useCallback, Suspense, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from '@/components/Header';
import { Radar } from '@/components/Radar';
import { RadarSidebar } from '@/components/RadarSidebar';
import { WatchlistPanel } from '@/components/WatchlistPanel';
import { DetailPanel } from '@/components/DetailPanel';
import { useRadarData } from '@/hooks/useRadarData';
import type { AITechnology, AIRadarData, Technology } from '@/lib/types';
import { Spinner } from '@/components/ui/spinner';
import { WarningCircle } from '@phosphor-icons/react';
import { matchesTechnologySearch } from '@/lib/radar-search';

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <Spinner className="w-8 h-8" />
      <div className="flex flex-col items-center gap-2">
        <p className="text-sm text-muted-foreground font-medium">
          Cargando tecnologías...
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
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
    >
      <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center">
        <WarningCircle className="w-8 h-8 text-destructive" weight="duotone" />
      </div>
      <div className="text-center max-w-md">
        <h3 className="text-lg font-semibold mb-1">Error al cargar</h3>
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
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
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
        <h3 className="text-lg font-semibold mb-1">Sin tecnologías</h3>
        <p className="text-sm text-muted-foreground">
          No se encontraron tecnologías. Intenta recargar la página.
        </p>
      </div>
    </motion.div>
  );
}

export default function Home() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTech, setSelectedTech] = useState<Technology | AITechnology | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const { data, loading, error } = useRadarData('ai');

  const aiData = data as AIRadarData | null;

  const handleSelect = useCallback((tech: Technology | AITechnology) => {
    setSelectedTech(tech);
    setPanelOpen(true);
  }, []);

  const handleClosePanel = useCallback(() => {
    setPanelOpen(false);
  }, []);

  const technologies = aiData?.technologies || [];
  const watchlist = aiData?.watchlist || [];
  const visibleTechnologies = useMemo(
    () => technologies.filter((technology) => matchesTechnologySearch(technology, searchQuery)),
    [technologies, searchQuery],
  );
  const visibleWatchlist = useMemo(
    () => watchlist.filter((technology) => matchesTechnologySearch(technology, searchQuery)),
    [watchlist, searchQuery],
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
              transition={{ type: "spring", stiffness: 100, damping: 20 }}
            >
              <div className="min-w-0">
                <div className="bento-card flex items-center justify-center p-3 sm:p-4">
                  <Suspense fallback={<LoadingState />}>
                    <Radar
                      technologies={technologies}
                      selectedTech={selectedTech}
                      searchQuery={searchQuery}
                      onSelect={handleSelect}
                    />
                  </Suspense>
                </div>

                <WatchlistPanel
                  watchlist={visibleWatchlist}
                  meta={aiData?.meta}
                  onSelectTechnology={handleSelect}
                />
              </div>

              <RadarSidebar
                visibleTechnologies={visibleTechnologies}
                totalTechnologies={technologies.length}
                selectedTechnologyId={selectedTech?.id ?? null}
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
