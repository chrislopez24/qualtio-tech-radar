'use client';

import { motion } from 'framer-motion';
import { Sparkle } from '@phosphor-icons/react';
import { SPRING_SNAPPY } from '@/lib/animation-constants';

export function AIIndicator() {
  return (
    <motion.div 
      className="group flex cursor-pointer items-center gap-2 rounded-xl border border-border/60 bg-bg-secondary px-3 py-2 transition-colors hover:border-primary/30 hover:bg-muted/70"
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={SPRING_SNAPPY}
    >
      <motion.div
        whileHover={{
          rotate: [0, 15, -15, 0],
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 0.6,
          ease: "easeInOut",
        }}
      >
        <Sparkle 
          className="h-4 w-4 text-primary transition-all"
          weight="fill" 
        />
      </motion.div>
      <span className="text-sm font-medium text-text-secondary transition-colors group-hover:text-white">
        AI
      </span>
      
      {/* Status indicator */}
      <div className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_10px_rgba(217,109,31,0.35)]" />
    </motion.div>
  );
}
