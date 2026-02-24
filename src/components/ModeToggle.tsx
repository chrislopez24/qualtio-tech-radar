'use client';

import { motion } from 'framer-motion';
import { Edit3, Sparkles } from 'lucide-react';
import type { Mode } from '@/lib/types';

interface ModeToggleProps {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  disabled?: boolean;
}

export function ModeToggle({ mode, onModeChange, disabled }: ModeToggleProps) {
  return (
    <div className="flex items-center gap-2 p-1 bg-muted rounded-lg">
      <button
        onClick={() => onModeChange('manual')}
        disabled={disabled}
        className={`
          flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium
          transition-colors duration-200
          ${mode === 'manual' 
            ? 'bg-background text-foreground shadow-sm' 
            : 'text-muted-foreground hover:text-foreground'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        <Edit3 className="w-4 h-4" />
        Manual
      </button>
      <button
        onClick={() => onModeChange('ai')}
        disabled={disabled}
        className={`
          flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium
          transition-colors duration-200
          ${mode === 'ai' 
            ? 'bg-background text-foreground shadow-sm' 
            : 'text-muted-foreground hover:text-foreground'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        <Sparkles className="w-4 h-4" />
        AI
      </button>
    </div>
  );
}