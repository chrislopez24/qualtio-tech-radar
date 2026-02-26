'use client';

import { motion } from 'framer-motion';
import { Sparkle } from '@phosphor-icons/react';

export function ModeToggle() {
  return (
    <motion.div 
      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#12121a] border border-[#ffffff08]
                 hover:border-[#00d4ff]/20 transition-colors cursor-pointer group"
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 400, damping: 17 }}
    >
      <motion.div
        animate={{
          rotate: [0, 15, -15, 0],
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          repeatDelay: 1,
          ease: "easeInOut",
        }}
      >
        <Sparkle 
          className="w-4 h-4 text-[#00d4ff] group-hover:text-glow-cyan transition-all" 
          weight="fill" 
        />
      </motion.div>
      <span className="text-sm font-medium text-[#a0a0b0] group-hover:text-white transition-colors">
        AI
      </span>
      
      {/* Status indicator */}
      <motion.div
        className="w-1.5 h-1.5 rounded-full bg-[#00d4ff]"
        animate={{
          boxShadow: [
            '0 0 0 0 rgba(0, 212, 255, 0.4)',
            '0 0 10px 2px rgba(0, 212, 255, 0.2)',
            '0 0 0 0 rgba(0, 212, 255, 0.4)',
          ],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
    </motion.div>
  );
}
