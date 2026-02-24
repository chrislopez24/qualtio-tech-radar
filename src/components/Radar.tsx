'use client';

import { useMemo } from 'react';
import * as d3 from 'd3';
import { motion } from 'framer-motion';
import type { Technology, AITechnology } from '@/lib/types';
import { QUADRANTS, RINGS, RADAR_SIZE } from '@/lib/radar-config';
import { useBlipPosition } from '@/hooks/useBlipPosition';
import { Blip } from './Blip';

interface RadarProps {
  technologies: (Technology | AITechnology)[];
  selectedTech: Technology | AITechnology | null;
  searchQuery: string;
  onSelect: (tech: Technology | AITechnology) => void;
}

export function Radar({
  technologies,
  selectedTech,
  searchQuery,
  onSelect,
}: RadarProps) {
  const { getPosition } = useBlipPosition(technologies);

  const filteredTechnologies = useMemo(() => {
    if (!searchQuery) return technologies;
    const query = searchQuery.toLowerCase();
    return technologies.filter(
      tech => tech.name.toLowerCase().includes(query) ||
              tech.description.toLowerCase().includes(query) ||
              tech.quadrant.includes(query) ||
              tech.ring.includes(query)
    );
  }, [technologies, searchQuery]);

  const filteredIds = new Set(filteredTechnologies.map(t => t.id));
  const center = RADAR_SIZE / 2;

  return (
    <div className="relative">
      <svg
        width={RADAR_SIZE}
        height={RADAR_SIZE}
        viewBox={`0 0 ${RADAR_SIZE} ${RADAR_SIZE}`}
        className="max-w-full h-auto"
      >
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <motion.g
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <circle
            cx={center}
            cy={center}
            r={RINGS[0].radius + 50}
            fill="url(#radarGradient)"
            opacity={0.1}
          />
          
          <defs>
            <radialGradient id="radarGradient" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.1} />
            </radialGradient>
          </defs>

          {RINGS.map((ring, index) => (
            <motion.circle
              key={ring.id}
              cx={center}
              cy={center}
              r={ring.radius}
              fill="none"
              stroke={ring.color}
              strokeWidth={2}
              strokeDasharray={index % 2 === 0 ? 'none' : '5 5'}
              opacity={0.6}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.6 }}
              transition={{ duration: 0.8, delay: index * 0.1 }}
            />
          ))}

          {QUADRANTS.map((quadrant, index) => {
            const nextQuadrant = QUADRANTS[(index + 1) % QUADRANTS.length];
            const angle1 = (quadrant.angle - 45) * Math.PI / 180;
            const angle2 = (nextQuadrant.angle - 45) * Math.PI / 180;
            
            const points = [
              `${center + RINGS[0].radius * Math.cos(angle1)},${center + RINGS[0].radius * Math.sin(angle1)}`,
              `${center + RINGS[0].radius * Math.cos(angle2)},${center + RINGS[0].radius * Math.sin(angle2)}`,
            ].join(' ');

            return (
              <motion.line
                key={quadrant.id}
                x1={center}
                y1={center}
                x2={center + RINGS[0].radius * Math.cos((quadrant.angle - 90) * Math.PI / 180)}
                y2={center + RINGS[0].radius * Math.sin((quadrant.angle - 90) * Math.PI / 180)}
                stroke={quadrant.color}
                strokeWidth={1}
                strokeDasharray="5 5"
                opacity={0.4}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.6, delay: index * 0.15 }}
              />
            );
          })}

          {RINGS.map((ring, index) => (
            <text
              key={`ring-label-${ring.id}`}
              x={center + 10}
              y={center - ring.radius + 20}
              fill={ring.color}
              fontSize={11}
              fontFamily="system-ui"
              opacity={0.8}
            >
              {ring.name}
            </text>
          ))}

          {QUADRANTS.map((quadrant, index) => {
            const labelRadius = RINGS[0].radius + 35;
            const angle = (quadrant.angle - 90) * Math.PI / 180;
            return (
              <text
                key={`quadrant-label-${quadrant.id}`}
                x={center + labelRadius * Math.cos(angle)}
                y={center + labelRadius * Math.sin(angle)}
                fill={quadrant.color}
                fontSize={14}
                fontFamily="system-ui"
                fontWeight={600}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {quadrant.name}
              </text>
            );
          })}
        </motion.g>

        <g>
          {technologies.map((tech, index) => {
            const position = getPosition(tech.id);
            if (!position) return null;

            return (
              <Blip
                key={tech.id}
                technology={tech}
                x={position.x}
                y={position.y}
                isSelected={selectedTech?.id === tech.id}
                isFiltered={searchQuery.length > 0 && !filteredIds.has(tech.id)}
                searchQuery={searchQuery}
                onSelect={onSelect}
              />
            );
          })}
        </g>
      </svg>
    </div>
  );
}