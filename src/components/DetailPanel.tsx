'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import type { Technology, AITechnology } from '@/lib/types';
import { getQuadrantById, getRingById } from '@/lib/radar-config';
import { EvidenceSummary } from './EvidenceSummary';
import {
  TrendUp,
  TrendDown,
  Minus,
  Star,
  ChatCircleText,
  CalendarBlank,
  Sparkle,
  ArrowUp,
  ArrowDown,
  X,
} from '@phosphor-icons/react';

interface DetailPanelProps {
  technology: Technology | AITechnology | null;
  open: boolean;
  onClose: () => void;
}

function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

function renderStringListSection(title: string, items?: string[]) {
  if (!items?.length) return null;
  return (
    <section>
      <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">{title}</h4>
      <ul className="mt-1 list-disc space-y-1 pl-4 text-muted-foreground">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export function DetailPanel({ technology, open, onClose }: DetailPanelProps) {
  const isOpen = open && technology !== null;
  if (!technology) {
    return null;
  }

  const quadrant = getQuadrantById(technology.quadrant);
  const ring = getRingById(technology.ring);
  const isAI = 'confidence' in technology;

  const aiTechnology = isAI ? (technology as AITechnology) : null;
  const trend = aiTechnology?.trend ?? 'stable';

  const trendVisual =
    trend === 'up'
      ? { label: 'Rising', icon: <TrendUp className="h-4 w-4 text-emerald-500" weight="fill" /> }
      : trend === 'down'
        ? { label: 'Declining', icon: <TrendDown className="h-4 w-4 text-rose-500" weight="fill" /> }
        : trend === 'new'
          ? { label: 'New', icon: <Sparkle className="h-4 w-4 text-amber-500" weight="fill" /> }
          : { label: 'Stable', icon: <Minus className="h-4 w-4 text-muted-foreground" weight="bold" /> };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.aside
          initial={{ opacity: 0, x: 24, scale: 0.98 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: 24, scale: 0.98 }}
          transition={{ type: 'spring', stiffness: 260, damping: 24 }}
          className="pointer-events-auto fixed bottom-4 right-4 z-40 w-[min(390px,calc(100vw-2rem))] rounded-2xl border border-border/70 bg-background/96 p-4 shadow-[0_20px_60px_-28px_rgba(15,23,42,0.55)] backdrop-blur-md lg:right-[390px]"
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

          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{technology.description}</p>

          {isAI && (
            <>
              <Separator className="my-3" />
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-lg border border-border/60 bg-muted/25 p-2">
                  <div className="flex items-center gap-1.5 text-muted-foreground">{trendVisual.icon}<span>Trend</span></div>
                  <p className="mt-1 text-sm font-semibold">{trendVisual.label}</p>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/25 p-2">
                  <div className="flex items-center gap-1.5 text-muted-foreground"><Sparkle className="h-4 w-4 text-cyan-500" weight="fill" /><span>Confidence</span></div>
                  <p className="mt-1 text-sm font-semibold">{Math.round((aiTechnology?.confidence ?? 0) * 100)}%</p>
                </div>

                {aiTechnology?.githubStars !== undefined && (
                  <div className="rounded-lg border border-border/60 bg-muted/25 p-2">
                    <div className="flex items-center gap-1.5 text-muted-foreground"><Star className="h-4 w-4 text-amber-500" weight="fill" /><span>GitHub</span></div>
                    <p className="mt-1 text-sm font-semibold">{formatNumber(aiTechnology.githubStars ?? 0)}</p>
                  </div>
                )}

                {aiTechnology?.hnMentions !== undefined && (
                  <div className="rounded-lg border border-border/60 bg-muted/25 p-2">
                    <div className="flex items-center gap-1.5 text-muted-foreground"><ChatCircleText className="h-4 w-4 text-orange-500" weight="fill" /><span>HN Mentions</span></div>
                    <p className="mt-1 text-sm font-semibold">{aiTechnology.hnMentions}</p>
                  </div>
                )}
              </div>

              {(aiTechnology?.whyNow || aiTechnology?.useCases?.length || aiTechnology?.avoidWhen?.length || aiTechnology?.risk) && (
                <>
                  <Separator className="my-3" />
                  <div className="space-y-3 text-sm">
                    {aiTechnology?.whyNow && (
                      <section>
                        <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Why now</h4>
                        <p className="mt-1 text-muted-foreground">{aiTechnology.whyNow}</p>
                      </section>
                    )}

                    {renderStringListSection('Use cases', aiTechnology?.useCases)}

                    {renderStringListSection('Avoid when', aiTechnology?.avoidWhen)}

                    {aiTechnology?.risk && (
                      <section>
                        <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Risks</h4>
                        <ul className="mt-1 space-y-1 text-muted-foreground">
                          {aiTechnology.risk.security && <li><strong>Security:</strong> {aiTechnology.risk.security}</li>}
                          {aiTechnology.risk.lockIn && <li><strong>Lock-in:</strong> {aiTechnology.risk.lockIn}</li>}
                          {aiTechnology.risk.talent && <li><strong>Talent:</strong> {aiTechnology.risk.talent}</li>}
                          {aiTechnology.risk.cost && <li><strong>Cost:</strong> {aiTechnology.risk.cost}</li>}
                        </ul>
                      </section>
                    )}
                  </div>
                </>
              )}

              {(aiTechnology?.whyThisRing || aiTechnology?.sourceCoverage || aiTechnology?.evidenceSummary || aiTechnology?.sourceFreshness) && (
                <>
                  <Separator className="my-3" />
                  <EvidenceSummary technology={aiTechnology} />
                </>
              )}

              {(aiTechnology?.sourceSummary || aiTechnology?.signalFreshness || aiTechnology?.owner || aiTechnology?.nextStep || aiTechnology?.nextReviewAt || aiTechnology?.evidence?.length || aiTechnology?.alternatives?.length) && (
                <>
                  <Separator className="my-3" />
                  <div className="space-y-3 text-sm">
                    {(aiTechnology.sourceSummary || aiTechnology.signalFreshness) && (
                      <section>
                        <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Data provenance</h4>
                        {aiTechnology.sourceSummary ? (
                          <p className="mt-1 text-muted-foreground">{aiTechnology.sourceSummary}</p>
                        ) : null}
                        {aiTechnology.signalFreshness ? (
                          <p className="mt-1 text-muted-foreground">Signal freshness: {aiTechnology.signalFreshness}</p>
                        ) : null}
                      </section>
                    )}

                    {(aiTechnology.owner || aiTechnology.nextReviewAt) && (
                      <section>
                        <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Owner & review</h4>
                        <p className="mt-1 text-muted-foreground">
                          {aiTechnology.owner ? `Owner: ${aiTechnology.owner}` : 'Owner: n/a'}
                          {aiTechnology.nextReviewAt ? ` · Next review: ${aiTechnology.nextReviewAt}` : ''}
                        </p>
                      </section>
                    )}

                    {aiTechnology.nextStep && (
                      <section>
                        <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Next step</h4>
                        <p className="mt-1 text-muted-foreground">{aiTechnology.nextStep}</p>
                      </section>
                    )}

                    {(aiTechnology.evidence?.length || aiTechnology.alternatives?.length) && (
                      <section>
                        <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Evidence / alternatives</h4>
                        {aiTechnology.evidence?.length ? (
                          <p className="mt-1 text-muted-foreground">Evidence: {aiTechnology.evidence.join(', ')}</p>
                        ) : null}
                        {aiTechnology.alternatives?.length ? (
                          <p className="mt-1 text-muted-foreground">Alternatives: {aiTechnology.alternatives.join(', ')}</p>
                        ) : null}
                      </section>
                    )}
                  </div>
                </>
              )}

            </>
          )}

          <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
            <CalendarBlank className="h-4 w-4" weight="duotone" />
            <span>
              Last updated{' '}
              {'updatedAt' in technology && technology.updatedAt
                ? new Date(technology.updatedAt).toLocaleDateString()
                : 'Unknown'}
            </span>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
