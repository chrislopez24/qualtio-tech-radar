'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Eye, Funnel } from '@phosphor-icons/react';
import type { AITechnology } from '@/lib/types';
import { QUADRANTS, RINGS } from '@/lib/radar-config';

type RingId = 'adopt' | 'trial' | 'assess' | 'hold';

const RING_ORDER: RingId[] = ['adopt', 'trial', 'assess', 'hold'];

interface RadarSidebarProps {
  visibleTechnologies: AITechnology[];
  totalTechnologies: number;
  selectedTechnologyId: string | null;
  onSelectTechnology: (technology: AITechnology) => void;
}

export function RadarSidebar({
  visibleTechnologies,
  totalTechnologies,
  selectedTechnologyId,
  onSelectTechnology,
}: RadarSidebarProps) {
  const hiddenCount = Math.max(0, totalTechnologies - visibleTechnologies.length);

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

  return (
    <aside className="bento-card flex h-[calc(100dvh-8rem)] min-h-[640px] flex-col overflow-hidden p-3">
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-xl border border-border/60 bg-background/80 p-2.5">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Eye className="h-3.5 w-3.5" weight="duotone" />
            Visible
          </div>
          <p className="mt-0.5 text-xl font-semibold tracking-tight">{visibleTechnologies.length}</p>
        </div>
        <div className="rounded-xl border border-border/60 bg-background/80 p-2.5">
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

      <div className="mt-2 min-h-0 flex-1 overflow-hidden rounded-xl border border-border/60 bg-background/90 p-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xl font-semibold tracking-tight">Technologies</h3>
          <span className="text-xs text-muted-foreground">Visible in radar</span>
        </div>

        <div className="h-full overflow-y-auto pr-1">
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
                        className={`flex w-full items-center gap-2.5 rounded-xl border px-2.5 py-2 text-left transition-colors ${
                          isSelected
                            ? 'border-primary/60 bg-primary/10'
                            : 'border-border/60 bg-background/70 hover:bg-muted/60'
                        }`}
                        whileTap={{ scale: 0.992 }}
                        transition={{ type: 'spring', stiffness: 420, damping: 28 }}
                      >
                        <span
                          className="inline-flex h-6 min-w-6 items-center justify-center rounded-full text-[10px] font-semibold text-white"
                          style={{ backgroundColor: ring.color }}
                        >
                          {index + 1}
                        </span>
                        <span className="truncate text-base font-medium leading-none">{technology.name}</span>
                      </motion.button>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
