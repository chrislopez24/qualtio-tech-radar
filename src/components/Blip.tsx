'use client';

import { useState, useCallback, memo } from 'react';
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
  onHoverChange: (technologyId: string | null) => void;
  onSelect: (tech: Technology | AITechnology) => void;
}

export const Blip = memo(function Blip({
  technology,
  x,
  y,
  isSelected,
  isFiltered,
  isHoveredExternal,
  onHoverChange,
  onSelect,
}: BlipProps) {
  const [isHoveredInternal, setIsHoveredInternal] = useState(false);

  const ring = getRingById(technology.ring);
  const baseColor = ring.color;
  const isHovered = isHoveredInternal || isHoveredExternal;

  const handleClick = useCallback(() => {
    onSelect(technology);
  }, [technology, onSelect]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(technology);
    }
  }, [technology, onSelect]);

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
  const outerRadius = isSelected ? 14 : isHovered ? 11 : 0;
  const mainRadius = isSelected ? 8 : isHovered ? 6.5 : 5.5;
  const innerRadius = isSelected ? 3.8 : isHovered ? 3 : 2.3;

  return (
    <g
      style={{
        cursor: 'pointer',
        opacity: isFiltered ? 0.22 : 1,
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
      {outerRadius > 0 ? (
        <circle
          cx={x}
          cy={y}
          r={outerRadius}
          fill="none"
          stroke={baseColor}
          strokeWidth={1}
          opacity={isSelected ? 0.4 : 0.22}
        />
      ) : null}

      <circle
        cx={x}
        cy={y}
        r={mainRadius}
        fill={baseColor}
        stroke={isSelected ? '#fff' : baseColor}
        strokeWidth={isSelected ? 1.8 : 1}
        style={{
          filter: isHovered || isSelected ? `drop-shadow(0 0 4px ${baseColor})` : 'none',
          transition: 'r 140ms ease, filter 140ms ease, stroke-width 140ms ease',
        }}
      />

      <circle
        cx={x}
        cy={y}
        r={innerRadius}
        fill="#fff"
        opacity={isHovered || isSelected ? 0.96 : 0.84}
      />

      {isSelected ? (
        <circle
          cx={x}
          cy={y}
          r={11}
          fill="none"
          stroke={baseColor}
          strokeWidth={1}
          strokeDasharray="4 4"
          opacity={0.5}
        />
      ) : null}

      {isHovered || isSelected ? (
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
    </g>
  );
});
