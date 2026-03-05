'use client';

import { motion } from 'framer-motion';
import { Sparkle } from '@phosphor-icons/react';
import { SPRING_SNAPPY } from '@/lib/animation-constants';

export function AIIndicator() {
  return (
    <motion.div 
      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-bg-secondary border border-border-subtle
                 hover:border-accent-cyan/20 transition-colors cursor-pointer group"
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
          className="w-4 h-4 text-accent-cyan group-hover:text-glow-cyan transition-all" 
          weight="fill" 
        />
      </motion.div>
      <span className="text-sm font-medium text-text-secondary group-hover:text-white transition-colors">
        AI
      </span>
      
      {/* Status indicator */}
      <div className="w-1.5 h-1.5 rounded-full bg-accent-cyan" />
    </motion.div>
  );
}
