'use client';

import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import type { Technology, AITechnology } from '@/lib/types';
import { getQuadrantById, getRingById, RADAR_SIZE } from '@/lib/radar-config';
import { TechnologyDetailContent } from './TechnologyDetailContent';
import { ArrowUp, ArrowDown, X } from '@phosphor-icons/react';

interface DetailPanelProps {
  technology: Technology | AITechnology | null;
  open: boolean;
  anchor: { x: number; y: number } | null;
  onClose: () => void;
  onExited?: () => void;
}

function getDesktopAnchorStyle(anchor: { x: number; y: number } | null): React.CSSProperties {
  if (!anchor) {
    return { right: '1rem', top: '50%', transform: 'translateY(-50%)' };
  }

  const attachLeft = anchor.x / RADAR_SIZE <= 0.58;
  const horizontalOffset = `${(anchor.x / RADAR_SIZE) * 100}%`;
  const verticalOffset = `${(anchor.y / RADAR_SIZE) * 100}%`;

  if (attachLeft) {
    return {
      left: `calc(${horizontalOffset} + 20px)`,
      top: verticalOffset,
      transform: 'translateY(-50%)',
    };
  }

  return {
    right: `calc(${((RADAR_SIZE - anchor.x) / RADAR_SIZE) * 100}% + 20px)`,
    top: verticalOffset,
    transform: 'translateY(-50%)',
  };
}

export function DetailPanel({ technology, open, anchor, onClose, onExited }: DetailPanelProps) {
  const isOpen = open && technology !== null;
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!technology) {
    return null;
  }

  const quadrant = getQuadrantById(technology.quadrant);
  const ring = getRingById(technology.ring);
  return (
    <AnimatePresence onExitComplete={onExited}>
      {isOpen && (
        <>
          <motion.button
            type="button"
            aria-label="Close details overlay"
            data-detail-overlay="true"
            className="fixed inset-0 z-20 bg-black/45 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          <motion.aside
            initial={{ opacity: 0, scale: 0.96, x: anchor && anchor.x / RADAR_SIZE > 0.58 ? -14 : 14, y: -8 }}
            animate={{ opacity: 1, scale: 1, x: 0, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, x: anchor && anchor.x / RADAR_SIZE > 0.58 ? -14 : 14, y: -8 }}
            transition={{ type: 'spring', stiffness: 260, damping: 24 }}
            className="pointer-events-auto absolute z-30 hidden w-[min(390px,42vw)] max-w-[390px] rounded-2xl border border-border/70 bg-background/96 p-4 shadow-[0_20px_60px_-28px_rgba(15,23,42,0.55)] backdrop-blur-md lg:block"
            style={getDesktopAnchorStyle(anchor)}
            data-detail-anchor={anchor ? `${anchor.x}:${anchor.y}` : 'none'}
            role="dialog"
            aria-modal="true"
            aria-label={`${technology.name} details`}
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
                  {technology.moved !== undefined && technology.moved !== 0 ? (
                    <Badge variant={technology.moved > 0 ? 'default' : 'destructive'} className="flex items-center gap-1">
                      {technology.moved > 0 ? <ArrowUp className="h-3 w-3" weight="bold" /> : <ArrowDown className="h-3 w-3" weight="bold" />}
                      {Math.abs(technology.moved)}
                    </Badge>
                  ) : null}
                </div>
              </div>

              <button
                ref={closeButtonRef}
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

          <motion.aside
            initial={{ opacity: 0, y: 32, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 32, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 260, damping: 24 }}
            className="pointer-events-auto fixed inset-x-0 bottom-0 z-40 max-h-[85vh] overflow-y-auto rounded-t-[1.75rem] border border-border/70 bg-background/98 p-4 shadow-[0_-20px_60px_-28px_rgba(15,23,42,0.7)] backdrop-blur-md lg:hidden"
            role="dialog"
            aria-modal="true"
            aria-label={`${technology.name} details`}
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
                </div>
              </div>

              <button
                type="button"
                ref={closeButtonRef}
                onClick={onClose}
                className="rounded-lg border border-border/70 p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                aria-label="Close details"
              >
                <X className="h-4 w-4" weight="bold" />
              </button>
            </div>

            <TechnologyDetailContent technology={technology} />
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
