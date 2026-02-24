'use client';

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import type { Technology, AITechnology } from '@/lib/types';
import { getQuadrantById, getRingById } from '@/lib/radar-config';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Star, 
  MessageSquare,
  Calendar,
  GitFork,
  Sparkles
} from 'lucide-react';

interface DetailPanelProps {
  technology: Technology | AITechnology | null;
  open: boolean;
  onClose: () => void;
}

export function DetailPanel({ technology, open, onClose }: DetailPanelProps) {
  if (!technology) return null;

  const quadrant = getQuadrantById(technology.quadrant);
  const ring = getRingById(technology.ring);
  const isAI = 'confidence' in technology;

  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up': return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'down': return <TrendingDown className="w-4 h-4 text-red-500" />;
      case 'new': return <Sparkles className="w-4 h-4 text-yellow-500" />;
      default: return <Minus className="w-4 h-4 text-gray-500" />;
    }
  };

  const getTrendLabel = (trend?: string) => {
    switch (trend) {
      case 'up': return 'Rising';
      case 'down': return 'Declining';
      case 'new': return 'New';
      default: return 'Stable';
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-md overflow-y-auto">
        <SheetHeader className="space-y-4">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-2xl font-bold">
              {technology.name}
            </SheetTitle>
            {technology.moved !== undefined && technology.moved !== 0 && (
              <Badge variant={technology.moved > 0 ? 'default' : 'destructive'}>
                {technology.moved > 0 ? '↑' : '↓'} Moved {Math.abs(technology.moved)} ring{Math.abs(technology.moved) > 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </SheetHeader>

        <div className="space-y-6 mt-6">
          <div className="flex gap-2">
            <Badge 
              style={{ 
                backgroundColor: `${ring.color}20`, 
                color: ring.color,
                borderColor: ring.color 
              }}
              className="border"
            >
              {ring.name}
            </Badge>
            <Badge 
              style={{ 
                backgroundColor: `${quadrant.color}20`, 
                color: quadrant.color,
                borderColor: quadrant.color 
              }}
              className="border"
            >
              {quadrant.name}
            </Badge>
          </div>

          <p className="text-muted-foreground leading-relaxed">
            {technology.description}
          </p>

          <Separator />

          {isAI && (
            <>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">AI Metrics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getTrendIcon((technology as AITechnology).trend)}
                      <span className="text-sm">Trend</span>
                    </div>
                    <Badge variant="outline">
                      {getTrendLabel((technology as AITechnology).trend)}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Star className="w-4 h-4 text-yellow-500" />
                      <span className="text-sm">GitHub Stars</span>
                    </div>
                    <span className="font-medium">
                      {formatNumber((technology as AITechnology).githubStars)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="w-4 h-4 text-orange-500" />
                      <span className="text-sm">HN Mentions</span>
                    </div>
                    <span className="font-medium">
                      {(technology as AITechnology).hnMentions}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-purple-500" />
                      <span className="text-sm">Confidence</span>
                    </div>
                    <span className="font-medium">
                      {Math.round((technology as AITechnology).confidence * 100)}%
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Separator />
            </>
          )}

          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="w-4 h-4" />
              <span>Last updated: {new Date('updatedAt' in technology ? technology.updatedAt : new Date().toISOString()).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}