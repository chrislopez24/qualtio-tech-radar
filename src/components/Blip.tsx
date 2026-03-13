'use client';

import { useState, useCallback, memo } from 'react';
import { motion } from 'framer-motion';
import type { Technology, AITechnology } from '@/lib/types';
import { getRingById } from '@/lib/radar-config';
import { getTooltipPosition } from '@/lib/blip-position';

interface BlipProps {
  technology: Technology | AITechnology;
  x: number;
  y: number;
  isSelected: boolean;
  isFiltered: boolean;
  isHoveredExternal: boolean;
  hasActiveSelection?: boolean;
  onHoverChange: (technologyId: string | null) => void;
  onSelect: (tech: Technology | AITechnology, anchor?: { x: number; y: number }) => void;
}

export const Blip = memo(function Blip({
  technology,
  x,
  y,
  isSelected,
  isFiltered,
  isHoveredExternal,
  hasActiveSelection = false,
  onHoverChange,
  onSelect,
}: BlipProps) {
  const [isHoveredInternal, setIsHoveredInternal] = useState(false);

  const ring = getRingById(technology.ring);
  const baseColor = ring.color;
  const isHovered = isHoveredInternal || isHoveredExternal;

  const handleClick = useCallback(() => {
    onSelect(technology, { x, y });
  }, [technology, onSelect, x, y]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(technology, { x, y });
    }
  }, [technology, onSelect, x, y]);

  const handlePointerEnter = useCallback(() => {
    setIsHoveredInternal(true);
    onHoverChange(technology.id);
  }, [technology.id, onHoverChange]);

  const handlePointerLeave = useCallback(() => {
    setIsHoveredInternal(false);
    onHoverChange(null);
  }, [onHoverChange]);

  const tooltipWidth = Math.min(technology.name.length * 8 + 24, 160);
  const tooltipPosition = getTooltipPosition({ x, y, width: tooltipWidth });
  const outerRadius = isSelected ? 16 : isHovered ? 11 : 0;
  const mainRadius = isSelected ? 7.4 : isHovered ? 6.5 : 5.5;
  const innerRadius = isSelected ? 2.8 : isHovered ? 3 : 2.3;

  return (
    <motion.g
      style={{
        cursor: 'pointer',
        opacity: isFiltered ? 0.22 : hasActiveSelection && !isSelected ? 0.38 : 1,
        transformOrigin: `${x}px ${y}px`,
        transition: 'opacity 140ms ease, transform 140ms ease',
        transform: isSelected ? 'scale(1.16)' : isHovered ? 'scale(1.08)' : 'scale(1)',
      }}
      tabIndex={isFiltered ? -1 : 0}
      role="button"
      aria-label={`${technology.name} - ${technology.ring} ring, ${technology.quadrant} quadrant`}
      onMouseEnter={handlePointerEnter}
      onMouseLeave={handlePointerLeave}
      onFocus={handlePointerEnter}
      onBlur={handlePointerLeave}
      onKeyDown={handleKeyDown}
      onClick={handleClick}
    >
      {isSelected ? (
        <motion.circle
          cx={x}
          cy={y}
          r={20}
          fill="none"
          stroke={baseColor}
          strokeWidth={1.5}
          opacity={0.18}
          initial={{ scale: 0.7, opacity: 0 }}
          animate={{ scale: [0.9, 1.12, 1], opacity: [0, 0.32, 0.18] }}
          transition={{ duration: 0.48, ease: [0.16, 1, 0.3, 1] }}
        />
      ) : null}

      {outerRadius > 0 ? (
        <motion.circle
          cx={x}
          cy={y}
          r={outerRadius}
          fill="none"
          stroke={baseColor}
          strokeWidth={isSelected ? 1.4 : 1}
          opacity={isSelected ? 0.45 : 0.22}
          initial={isSelected ? { scale: 0.82, opacity: 0 } : false}
          animate={isSelected ? { scale: 1, opacity: 0.45 } : undefined}
          transition={{ type: 'spring', stiffness: 320, damping: 24 }}
        />
      ) : null}

      <motion.circle
        cx={x}
        cy={y}
        r={mainRadius}
        fill={baseColor}
        stroke={baseColor}
        strokeWidth={isSelected ? 1.6 : 1}
        style={{
          filter: isHovered || isSelected ? `drop-shadow(0 0 7px ${baseColor})` : 'none',
          transition: 'r 140ms ease, filter 140ms ease, stroke-width 140ms ease',
        }}
        animate={isSelected ? { r: 7.4 } : isHovered ? { r: 6.5 } : { r: 5.5 }}
        transition={{ type: 'spring', stiffness: 360, damping: 22 }}
      />

      {!isSelected ? (
        <circle
          cx={x}
          cy={y}
          r={innerRadius}
          fill="#f6f1e8"
          opacity={isHovered ? 0.9 : 0.76}
        />
      ) : null}

      {isSelected ? (
        <motion.circle
          cx={x}
          cy={y}
          r={12}
          fill="none"
          stroke={baseColor}
          strokeWidth={1}
          strokeDasharray="4 4"
          opacity={0.55}
          animate={{ rotate: 12 }}
          transition={{ type: 'spring', stiffness: 140, damping: 18 }}
        />
      ) : null}

      {isHovered && !isSelected ? (
        <g>
          <rect
            x={tooltipPosition.x}
            y={tooltipPosition.y}
            width={tooltipWidth}
            height={26}
            rx={6}
            fill="rgba(10, 10, 15, 0.98)"
            stroke={baseColor}
            strokeWidth={1}
            style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.5))' }}
          />
          <text
            x={tooltipPosition.x + tooltipWidth / 2}
            y={tooltipPosition.y + 17}
            fill="#fff"
            fontSize={11}
            fontFamily="var(--font-sans)"
            fontWeight={500}
            textAnchor="middle"
            letterSpacing="0.02em"
          >
            {technology.name.length > 18 ? `${technology.name.slice(0, 15)}...` : technology.name}
          </text>
        </g>
      ) : null}
    </motion.g>
  );
});
