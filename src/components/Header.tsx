'use client';

import { motion } from 'framer-motion';
import { GithubLogo } from '@phosphor-icons/react';
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
      <div className="h-px w-full bg-gradient-to-r from-transparent via-accent-cyan/70 to-transparent" />
      
      {/* Header Content */}
      <div className="glass-panel border-b-0">
        <div className="max-w-[1600px] mx-auto px-6 lg:px-8 py-3.5">
          <div className="flex items-center justify-between gap-6">
            {/* Logo Section */}
            <div className="flex items-center gap-3">
              <motion.div 
                className="relative flex items-center overflow-hidden rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2 shadow-[0_0_0_1px_rgba(217,109,31,0.06)]"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.98 }}
                transition={SPRING_SNAPPY}
              >
                <img
                  src="/logo.png"
                  alt="Qualtio"
                  className="relative z-10 h-[28px] w-auto sm:h-[30px] lg:h-[32px]"
                />
              </motion.div>
              
              <div className="hidden sm:block leading-none">
                <motion.h1 
                  className="font-mono text-[11px] font-medium uppercase tracking-[0.28em] text-text-secondary"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  Qualtio
                </motion.h1>
                <motion.p 
                  className="mt-1 text-[10px] font-mono text-accent-cyan uppercase tracking-[0.32em]"
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
                className="rounded-xl p-3 transition-colors spring-transition group hover:bg-white/5"
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
