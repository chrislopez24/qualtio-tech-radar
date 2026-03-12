'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import type { Technology, AITechnology } from '@/lib/types';
import { getQuadrantById, getRingById } from '@/lib/radar-config';
import { TechnologyDetailContent } from './TechnologyDetailContent';
import { ArrowUp, ArrowDown, X } from '@phosphor-icons/react';

interface DetailPanelProps {
  technology: Technology | AITechnology | null;
  open: boolean;
  onClose: () => void;
}

export function DetailPanel({ technology, open, onClose }: DetailPanelProps) {
  const isOpen = open && technology !== null;
  if (!technology) {
    return null;
  }

  const quadrant = getQuadrantById(technology.quadrant);
  const ring = getRingById(technology.ring);
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.aside
          initial={{ opacity: 0, x: 24, scale: 0.98 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: 24, scale: 0.98 }}
          transition={{ type: 'spring', stiffness: 260, damping: 24 }}
          className="pointer-events-auto fixed bottom-4 right-4 z-40 w-[min(390px,calc(100vw-2rem))] rounded-2xl border border-border/70 bg-background/96 p-4 shadow-[0_20px_60px_-28px_rgba(15,23,42,0.55)] backdrop-blur-md lg:hidden"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-xl font-semibold tracking-tight">{technology.name}</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge style={{ backgroundColor: `${ring.color}15`, color: ring.color, borderColor: `${ring.color}30` }} className="border">
                  {ring.name}
                </Badge>
                <Badge style={{ backgroundColor: `${quadrant.color}15`, color: quadrant.color, borderColor: `${quadrant.color}30` }} className="border">
                  {quadrant.name}
                </Badge>
                {technology.moved !== undefined && technology.moved !== 0 && (
                  <Badge variant={technology.moved > 0 ? 'default' : 'destructive'} className="flex items-center gap-1">
                    {technology.moved > 0 ? <ArrowUp className="h-3 w-3" weight="bold" /> : <ArrowDown className="h-3 w-3" weight="bold" />}
                    {Math.abs(technology.moved)}
                  </Badge>
                )}
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-border/70 p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              aria-label="Close details"
            >
              <X className="h-4 w-4" weight="bold" />
            </button>
          </div>

          <TechnologyDetailContent technology={technology} />
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
