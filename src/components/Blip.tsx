'use client';

import { useState, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Technology, AITechnology } from '@/lib/types';
import { getRingById } from '@/lib/radar-config';
import { RADAR_SIZE } from '@/lib/radar-config';

interface BlipProps {
  technology: Technology | AITechnology;
  x: number;
  y: number;
  isSelected: boolean;
  isFiltered: boolean;
  onSelect: (tech: Technology | AITechnology) => void;
}

export const Blip = memo(function Blip({
  technology,
  x,
  y,
  isSelected,
  isFiltered,
  onSelect,
}: BlipProps) {
  const [isHovered, setIsHovered] = useState(false);

  const ring = getRingById(technology.ring);
  const baseColor = ring.color;

  const handleClick = useCallback(() => {
    onSelect(technology);
  }, [technology, onSelect]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(technology);
    }
  }, [technology, onSelect]);

  // Calculate tooltip position to avoid clipping
  const tooltipWidth = Math.min(technology.name.length * 8 + 24, 160);
  const tooltipX = x + 18;
  const tooltipY = y - 14;
  
  // Adjust if tooltip overflows right edge
  const adjustedX = tooltipX + tooltipWidth > RADAR_SIZE - 20 
    ? x - tooltipWidth - 18 
    : tooltipX;

  return (
    <motion.g
      initial={{ opacity: 0, scale: 0 }}
      animate={{ 
        opacity: isFiltered ? 0.15 : 1, 
        scale: isSelected ? 1.4 : isHovered ? 1.2 : 1 
      }}
      transition={{ 
        type: "spring",
        stiffness: 400,
        damping: 25
      }}
      style={{ cursor: 'pointer' }}
      tabIndex={isFiltered ? -1 : 0}
      role="button"
      aria-label={`${technology.name} - ${technology.ring} ring, ${technology.quadrant} quadrant`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onFocus={() => setIsHovered(true)}
      onBlur={() => setIsHovered(false)}
      onKeyDown={handleKeyDown}
      onClick={handleClick}
    >
      {/* Outer glow ring */}
      {(isHovered || isSelected) && (
        <motion.circle
          cx={x}
          cy={y}
          r={isSelected ? 16 : 12}
          fill="none"
          stroke={baseColor}
          strokeWidth={1}
          opacity={0.2}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ 
            scale: [1, 1.15, 1],
            opacity: [0.2, 0.1, 0.2]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      )}
      
      {/* Main blip */}
      <motion.circle
        cx={x}
        cy={y}
        r={isSelected ? 9 : isHovered ? 7 : 6}
        fill={baseColor}
        stroke={isSelected ? '#fff' : baseColor}
        strokeWidth={isSelected ? 2 : 1}
        style={{
          filter: isHovered || isSelected 
            ? `drop-shadow(0 0 6px ${baseColor})` 
            : 'none',
        }}
      />
      
      {/* Inner core */}
      <motion.circle
        cx={x}
        cy={y}
        r={isSelected ? 4 : isHovered ? 3 : 2.5}
        fill="#fff"
        opacity={isHovered || isSelected ? 0.95 : 0.8}
      />
      
      {/* Rotating selection ring */}
      {isSelected && (
        <motion.circle
          cx={x}
          cy={y}
          r={12}
          fill="none"
          stroke={baseColor}
          strokeWidth={1}
          strokeDasharray="4 4"
          initial={{ rotate: 0 }}
          animate={{ rotate: 360 }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "linear"
          }}
          style={{
            transformOrigin: `${x}px ${y}px`,
            opacity: 0.5
          }}
        />
      )}
      
      {/* Smart-positioned tooltip */}
      <AnimatePresence>
        {(isHovered || isSelected) && (
          <motion.g
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ 
              duration: 0.2,
              ease: [0.16, 1, 0.3, 1]
            }}
          >
            {/* Tooltip Background */}
            <motion.rect
              x={adjustedX}
              y={tooltipY}
              width={tooltipWidth}
              height={26}
              rx={6}
              fill="rgba(10, 10, 15, 0.98)"
              stroke={baseColor}
              strokeWidth={1}
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
              style={{
                filter: `drop-shadow(0 4px 12px rgba(0,0,0,0.5))`
              }}
            />
            
            {/* Tooltip Text */}
            <text
              x={adjustedX + tooltipWidth / 2}
              y={tooltipY + 17}
              fill="#fff"
              fontSize={11}
              fontFamily="var(--font-sans)"
              fontWeight={500}
              textAnchor="middle"
              letterSpacing="0.02em"
            >
              {technology.name.length > 18 
                ? technology.name.slice(0, 15) + '...' 
                : technology.name}
            </text>
          </motion.g>
        )}
      </AnimatePresence>
    </motion.g>
  );
});
