'use client';

import { motion } from 'framer-motion';
import { QUADRANTS, RINGS } from '@/lib/radar-config';
import { Circle, Square } from '@phosphor-icons/react';
import { SPRING_SMOOTH, SPRING_SNAPPY } from '@/lib/animation-constants';

const containerVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      ...SPRING_SMOOTH,
      staggerChildren: 0.08,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      ...SPRING_SMOOTH,
    },
  },
};

export function Legend() {
  return (
    <motion.div 
      className="glass-panel rounded-2xl p-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="mb-6">
        <h3 className="font-display text-sm font-semibold tracking-tight text-white mb-1">
          Radar Guide
        </h3>
        <p className="text-xs text-text-tertiary font-mono uppercase tracking-widest">
          Classification System
        </p>
      </motion.div>

      {/* Rings Section */}
      <div className="mb-6">
        <motion.h4 
          variants={itemVariants}
          className="text-xs font-mono text-text-tertiary uppercase tracking-widest mb-3 flex items-center gap-2"
        >
          <Circle className="w-3 h-3" weight="duotone" />
          Rings
        </motion.h4>
        <motion.div 
          className="space-y-2"
          variants={containerVariants}
        >
          {RINGS.map((ring) => (
            <motion.div 
              key={ring.id} 
              className="flex items-center gap-3 group cursor-pointer p-2 -mx-2 rounded-lg hover:bg-white/5 transition-colors"
              variants={itemVariants}
              whileHover={{ x: 4 }}
              transition={SPRING_SNAPPY}
            >
              <div className="relative">
                <motion.div
                  className="w-3 h-3 rounded-full"
                  style={{ 
                    backgroundColor: ring.color,
                    boxShadow: `0 0 10px ${ring.color}40`
                  }}
                  whileHover={{ scale: 1.3 }}
                  transition={SPRING_SNAPPY}
                />
              </div>
              <div className="flex-1">
                <span className="text-sm text-text-secondary group-hover:text-white transition-colors font-medium">
                  {ring.name}
                </span>
              </div>
              <span className="text-xs font-mono text-text-tertiary">
                {ring.id}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Divider */}
      <motion.div 
        variants={itemVariants}
        className="h-px bg-gradient-to-r from-transparent via-border-subtle to-transparent my-6" 
      />

      {/* Quadrants Section */}
      <div>
        <motion.h4 
          variants={itemVariants}
          className="text-xs font-mono text-text-tertiary uppercase tracking-widest mb-3 flex items-center gap-2"
        >
          <Square className="w-3 h-3" weight="duotone" />
          Quadrants
        </motion.h4>
        <motion.div 
          className="space-y-2"
          variants={containerVariants}
        >
          {QUADRANTS.map((quadrant) => (
            <motion.div 
              key={quadrant.id} 
              className="flex items-center gap-3 group cursor-pointer p-2 -mx-2 rounded-lg hover:bg-white/5 transition-colors"
              variants={itemVariants}
              whileHover={{ x: 4 }}
              transition={SPRING_SNAPPY}
            >
              <div className="relative">
                <motion.div
                  className="w-3 h-3 rounded"
                  style={{ 
                    backgroundColor: quadrant.color,
                    boxShadow: `0 0 10px ${quadrant.color}40`
                  }}
                  whileHover={{ scale: 1.3 }}
                  transition={SPRING_SNAPPY}
                />
              </div>
              <div className="flex-1">
                <span className="text-sm text-text-secondary group-hover:text-white transition-colors font-medium">
                  {quadrant.name}
                </span>
              </div>
              <span className="text-xs font-mono text-text-tertiary">
                {quadrant.id.slice(0, 2).toUpperCase()}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </motion.div>
  );
}
