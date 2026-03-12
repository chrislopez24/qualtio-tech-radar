'use client';

import { motion } from 'framer-motion';
import type { Technology, AITechnology } from '@/lib/types';
import { QUADRANTS, RINGS, RADAR_SIZE } from '@/lib/radar-config';
import { useBlipPosition } from '@/hooks/useBlipPosition';
import { Blip } from './Blip';

interface RadarProps {
  technologies: (Technology | AITechnology)[];
  allTechnologies?: (Technology | AITechnology)[];
  selectedTech: Technology | AITechnology | null;
  hoveredTechnologyId: string | null;
  onHoverTechnology: (technologyId: string | null) => void;
  onSelect: (tech: Technology | AITechnology) => void;
}

export function Radar({
  technologies,
  allTechnologies = technologies,
  selectedTech,
  hoveredTechnologyId,
  onHoverTechnology,
  onSelect,
}: RadarProps) {
  const { getPosition } = useBlipPosition(technologies, allTechnologies);
  const center = RADAR_SIZE / 2;

  return (
    <div className="relative">
      {/* Background Grid Effect */}
      <div className="absolute inset-0 opacity-10">
        <div 
          className="w-full h-full"
          style={{
            backgroundImage: `
              radial-gradient(circle at ${center}px ${center}px, rgba(249, 115, 22, 0.06) 0%, rgba(99, 102, 241, 0.025) 42%, transparent 66%),
              linear-gradient(rgba(249, 115, 22, 0.018) 1px, transparent 1px),
              linear-gradient(90deg, rgba(99, 102, 241, 0.018) 1px, transparent 1px)
            `,
            backgroundSize: '100% 100%, 60px 60px, 60px 60px',
          }}
        />
      </div>
      
      <svg
        width={RADAR_SIZE}
        height={RADAR_SIZE}
        viewBox={`0 0 ${RADAR_SIZE} ${RADAR_SIZE}`}
        className="max-w-full h-auto relative z-10"
        role="img"
        aria-label="Technology radar visualization showing technologies across four quadrants and maturity rings"
      >
        <defs>
          {/* Glow Filters */}
          <filter id="glow-soft" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          
          {/* Radial Gradient for center glow */}
          <radialGradient id="radarCenterGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#f97316" stopOpacity={0.055} />
            <stop offset="45%" stopColor="#6366f1" stopOpacity={0.02} />
            <stop offset="100%" stopColor="transparent" stopOpacity={0} />
          </radialGradient>
        </defs>

        {/* Background Glow */}
        <motion.circle
          cx={center}
          cy={center}
          r={RINGS[0].radius + 50}
          fill="url(#radarCenterGlow)"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ 
            type: "spring", 
            stiffness: 30, 
            damping: 20,
            delay: 0.2 
          }}
        />

        {/* Quadrant background fills */}
        {QUADRANTS.map((quadrant) => {
          const startAngle = (quadrant.angle - 90) * Math.PI / 180;
          const endAngle = startAngle + Math.PI / 2;
          const outerRadius = RINGS[0].radius;
          const largeArcFlag = 0;
          return (
            <path
              key={`quadrant-fill-${quadrant.id}`}
              d={`M ${center} ${center}
                  L ${center + outerRadius * Math.cos(startAngle)} ${center + outerRadius * Math.sin(startAngle)}
                  A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${center + outerRadius * Math.cos(endAngle)} ${center + outerRadius * Math.sin(endAngle)}
                  Z`}
              fill={quadrant.color}
              opacity={0.04}
            />
          );
        })}

        {/* Radar Rings */}
        <motion.g
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          {RINGS.map((ring, index) => (
            <motion.circle
              key={ring.id}
              cx={center}
              cy={center}
              r={ring.radius}
              fill="none"
              stroke={ring.color}
              strokeWidth={1.5}
              strokeDasharray={index % 2 === 0 ? 'none' : '8 4'}
              opacity={0.5}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.5 }}
              transition={{ 
                duration: 1.2, 
                delay: index * 0.15,
                ease: [0.16, 1, 0.3, 1]
              }}
            />
          ))}

          {/* Quadrant Lines */}
          {QUADRANTS.map((quadrant, index) => {
            return (
              <motion.line
                key={quadrant.id}
                x1={center}
                y1={center}
                x2={center + RINGS[0].radius * Math.cos((quadrant.angle - 90) * Math.PI / 180)}
                y2={center + RINGS[0].radius * Math.sin((quadrant.angle - 90) * Math.PI / 180)}
                stroke={quadrant.color}
                strokeWidth={1.5}
                strokeDasharray="8 4"
                opacity={0.35}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ 
                  duration: 0.8, 
                  delay: index * 0.2,
                  ease: [0.16, 1, 0.3, 1]
                }}
              />
            );
          })}

          {/* Ring Labels */}
          {RINGS.map((ring, index) => (
            <motion.text
              key={`ring-label-${ring.id}`}
              x={center + 16}
              y={center - ring.radius + (ring.id === 'hold' ? 20 : ring.id === 'assess' ? 16 : ring.id === 'trial' ? 14 : 12)}
              fill={ring.color}
              fontSize={10}
              fontFamily="var(--font-mono)"
              fontWeight={500}
              opacity={0.7}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 0.7, x: 0 }}
              transition={{ delay: 0.6 + index * 0.1 }}
            >
              {ring.name}
            </motion.text>
          ))}

          {/* Quadrant Labels */}
          {QUADRANTS.map((quadrant, index) => {
            const labelRadius = RINGS[0].radius + 40;
            const angle = (quadrant.angle - 90) * Math.PI / 180;
            const rawX = center + labelRadius * Math.cos(angle);
            const rawY = center + labelRadius * Math.sin(angle);
            // Clamp to keep within SVG bounds
            const x = Math.max(70, Math.min(RADAR_SIZE - 70, rawX));
            const y = Math.max(25, Math.min(RADAR_SIZE - 25, rawY));
            
            return (
              <motion.g 
                key={`quadrant-label-${quadrant.id}`}
                initial={{ opacity: 0, scale: 0.8, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ 
                  delay: 0.7 + index * 0.1,
                  type: "spring",
                  stiffness: 100,
                  damping: 20
                }}
              >
                {/* Label Background */}
                <rect
                  x={x - 48}
                  y={y - 14}
                  width={96}
                  height={28}
                  rx={8}
                  fill="rgba(10, 10, 15, 0.95)"
                  stroke={quadrant.color}
                  strokeWidth={1}
                  opacity={0.95}
                />
                
                {/* Label Text */}
                <text
                  x={x}
                  y={y + 1}
                  fill={quadrant.color}
                  fontSize={11}
                  fontFamily="var(--font-sans)"
                  fontWeight={600}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  letterSpacing="0.08em"
                >
                  {quadrant.name.toUpperCase()}
                </text>
              </motion.g>
            );
          })}
        </motion.g>

        {/* Technology Blips */}
        <g>
          {technologies.map((tech) => {
            const position = getPosition(tech.id);
            if (!position) return null;

            return (
              <g key={tech.id}>
                <Blip
                  technology={tech}
                  x={position.x}
                  y={position.y}
                  isSelected={selectedTech?.id === tech.id}
                  isFiltered={Boolean(
                    hoveredTechnologyId &&
                    hoveredTechnologyId !== tech.id &&
                    selectedTech?.id !== tech.id,
                  )}
                  isHoveredExternal={hoveredTechnologyId === tech.id}
                  hasActiveSelection={Boolean(selectedTech)}
                  onHoverChange={onHoverTechnology}
                  onSelect={onSelect}
                />
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
