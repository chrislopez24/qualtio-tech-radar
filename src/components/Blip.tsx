'use client';

import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import type { Technology, AITechnology } from '@/lib/types';
import { getQuadrantById, getRingById } from '@/lib/radar-config';

interface BlipProps {
  technology: Technology | AITechnology;
  x: number;
  y: number;
  isSelected: boolean;
  isFiltered: boolean;
  searchQuery: string;
  onSelect: (tech: Technology | AITechnology) => void;
}

export function Blip({
  technology,
  x,
  y,
  isSelected,
  isFiltered,
  searchQuery,
  onSelect,
}: BlipProps) {
  const [isHovered, setIsHovered] = useState(false);

  const quadrant = getQuadrantById(technology.quadrant);
  const ring = getRingById(technology.ring);
  const baseColor = ring.color;
  const opacity = isFiltered ? 0.3 : 1;
  const scale = isSelected ? 1.5 : isHovered ? 1.2 : 1;

  const handleClick = useCallback(() => {
    onSelect(technology);
  }, [technology, onSelect]);

  const matchesSearch = searchQuery.length > 0 && 
    technology.name.toLowerCase().includes(searchQuery.toLowerCase());

  return (
    <motion.g
      initial={{ opacity: 0, scale: 0 }}
      animate={{ 
        opacity: isFiltered ? 0.3 : 1, 
        scale: isSelected ? 1.5 : isHovered ? 1.2 : 1 
      }}
      transition={{ 
        duration: 0.3,
        type: 'spring',
        stiffness: 300,
        damping: 20
      }}
      style={{ cursor: 'pointer' }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleClick}
    >
      <circle
        cx={x}
        cy={y}
        r={isSelected ? 12 : isHovered ? 10 : 8}
        fill={baseColor}
        fillOpacity={0.8}
        stroke={isSelected ? '#fff' : baseColor}
        strokeWidth={isSelected ? 3 : 2}
        style={{
          filter: isHovered || isSelected 
            ? `drop-shadow(0 0 8px ${baseColor})` 
            : 'none',
          transition: 'all 0.2s ease',
        }}
      />
      
      {isSelected && (
        <circle
          cx={x}
          cy={y}
          r={16}
          fill="none"
          stroke={baseColor}
          strokeWidth={1}
          strokeDasharray="4 4"
        >
          <animateTransform
            attributeName="transform"
            type="rotate"
            from={`0 ${x} ${y}`}
            to={`360 ${x} ${y}`}
            dur="3s"
            repeatCount="indefinite"
          />
        </circle>
      )}
      
      {(isHovered || isSelected) && (
        <g>
          <rect
            x={x + 15}
            y={y - 10}
            width={technology.name.length * 8 + 16}
            height={24}
            rx={4}
            fill="rgba(0, 0, 0, 0.8)"
          />
          <text
            x={x + 23}
            y={y + 5}
            fill="#fff"
            fontSize={12}
            fontFamily="system-ui"
            fontWeight={500}
          >
            {technology.name}
          </text>
        </g>
      )}
    </motion.g>
  );
}