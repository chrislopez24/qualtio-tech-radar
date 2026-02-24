'use client';

import { useState, useCallback } from 'react';
import { Header } from '@/components/Header';
import { Radar } from '@/components/Radar';
import { Legend } from '@/components/Legend';
import { DetailPanel } from '@/components/DetailPanel';
import { useRadarData } from '@/hooks/useRadarData';
import type { Mode, Technology, AITechnology } from '@/lib/types';
import { Loader2, AlertCircle } from 'lucide-react';

export default function Home() {
  const [mode, setMode] = useState<Mode>('manual');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTech, setSelectedTech] = useState<Technology | AITechnology | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const { data, loading, error } = useRadarData(mode);

  const handleSelect = useCallback((tech: Technology | AITechnology) => {
    setSelectedTech(tech);
    setPanelOpen(true);
  }, []);

  const handleClosePanel = useCallback(() => {
    setPanelOpen(false);
  }, []);

  const technologies = data?.technologies || [];

  return (
    <div className="min-h-screen bg-background">
      <Header
        mode={mode}
        onModeChange={setMode}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <main className="container mx-auto px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center min-h-[60vh]">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center min-h-[60vh] gap-2 text-destructive">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        ) : (
          <div className="flex flex-col lg:flex-row items-start justify-center gap-8">
            <div className="flex-1 flex justify-center">
              <Radar
                technologies={technologies}
                selectedTech={selectedTech}
                searchQuery={searchQuery}
                onSelect={handleSelect}
              />
            </div>
            
            <div className="hidden lg:block">
              <Legend />
            </div>
          </div>
        )}
      </main>

      <DetailPanel
        technology={selectedTech}
        open={panelOpen}
        onClose={handleClosePanel}
      />
    </div>
  );
}