'use client';

import { motion } from 'framer-motion';
import { GithubLogo, Compass } from '@phosphor-icons/react';
import { AIIndicator } from './ModeToggle';
import { SearchBar } from './SearchBar';
import { SPRING_SMOOTH, SPRING_SNAPPY } from '@/lib/animation-constants';

interface HeaderProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
}

export function Header({ 
  searchQuery, 
  onSearchChange 
}: HeaderProps) {
  return (
    <motion.header 
      className="fixed top-0 left-0 right-0 z-50"
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={SPRING_SMOOTH}
    >
      {/* Gradient Line */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-accent-cyan/50 to-transparent" />
      
      {/* Header Content */}
      <div className="glass-panel border-b-0">
        <div className="max-w-[1600px] mx-auto px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between gap-6">
            {/* Logo Section */}
            <div className="flex items-center gap-4">
              <motion.div 
                className="relative w-11 h-11 rounded-xl flex items-center justify-center overflow-hidden group"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.98 }}
                transition={SPRING_SNAPPY}
              >
                {/* Background Glow */}
                <div className="absolute inset-0 bg-gradient-to-br from-[#00d4ff] to-[#ff006e] opacity-80 group-hover:opacity-100 transition-opacity" />
                
                {/* Animated Border */}
                <div className="absolute inset-0 rounded-xl border-2 border-white/20 group-hover:shadow-[0_0_20px_2px_rgba(0,212,255,0.3)] transition-shadow duration-300" />
                
                <Compass className="w-6 h-6 text-white relative z-10" weight="fill" />
              </motion.div>
              
              <div className="hidden sm:block">
                <motion.h1 
                  className="font-display text-xl font-bold tracking-tight text-white"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  <span className="text-glow-cyan">Q</span>ualtio
                </motion.h1>
                <motion.p 
                  className="text-xs font-mono text-text-tertiary uppercase tracking-widest"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                >
                  Tech Radar
                </motion.p>
              </div>
            </div>

            {/* Center - Search */}
            <div className="flex-1 max-w-md mx-4 hidden md:block">
              <SearchBar value={searchQuery} onChange={onSearchChange} />
            </div>

            {/* Right Section */}
            <div className="flex items-center gap-2">
              <AIIndicator />
              
              <motion.a
                href="https://github.com/chrislopez24/qualtio-tech-radar"
                target="_blank"
                rel="noopener noreferrer"
                className="p-3 rounded-xl hover:bg-white/5 transition-colors spring-transition group"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                transition={SPRING_SNAPPY}
                aria-label="Open GitHub repository"
              >
                <GithubLogo 
                  className="w-5 h-5 text-text-secondary group-hover:text-white transition-colors" 
                  weight="duotone" 
                />
              </motion.a>
            </div>
          </div>
          
          {/* Mobile Search */}
          <div className="mt-3 md:hidden">
            <SearchBar value={searchQuery} onChange={onSearchChange} />
          </div>
        </div>
      </div>
    </motion.header>
  );
}
