'use client';

import { motion } from 'framer-motion';
import Image from 'next/image';
import { GithubLogo } from '@phosphor-icons/react';
import { AIIndicator } from './ModeToggle';
import { SearchBar } from './SearchBar';
import { SPRING_SMOOTH, SPRING_SNAPPY } from '@/lib/animation-constants';
import { getPublicAssetPath } from '@/lib/public-asset';

interface HeaderProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
}

export function Header({ 
  searchQuery, 
  onSearchChange 
}: HeaderProps) {
  const logoSrc = getPublicAssetPath('/logo.png');

  return (
    <motion.header
      className="fixed left-0 right-0 top-0 z-50 border-b border-border/50 bg-background/92 backdrop-blur-xl"
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={SPRING_SMOOTH}
    >
      <div className="h-px w-full bg-gradient-to-r from-transparent via-primary/50 to-transparent" />

      <div>
        <div className="mx-auto max-w-[1760px] px-3 py-2.5 sm:px-5 lg:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <motion.div
                className="relative flex items-center overflow-hidden rounded-xl border border-border/70 bg-bg-secondary px-2.5 py-1.5"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.98 }}
                transition={SPRING_SNAPPY}
              >
                <Image
                  src={logoSrc}
                  alt="Qualtio"
                  width={132}
                  height={30}
                  className="relative z-10 h-[22px] w-auto sm:h-[26px]"
                />
              </motion.div>

              <div className="hidden sm:block leading-none">
                <motion.p
                  className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.12 }}
                >
                  Tech Radar
                </motion.p>
                <motion.p
                  className="mt-1 text-[10px] font-medium text-text-tertiary"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                >
                  Editorial market snapshot
                </motion.p>
              </div>
            </div>

            <div className="mx-2 hidden max-w-xl flex-1 md:block">
              <SearchBar value={searchQuery} onChange={onSearchChange} />
            </div>

            <div className="flex items-center gap-2">
              <AIIndicator />

              <motion.a
                href="https://github.com/chrislopez24/qualtio-tech-radar"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-xl border border-border/60 bg-bg-secondary p-2.5 transition-colors spring-transition group hover:bg-muted/70"
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
          
          <div className="mt-2 md:hidden">
            <SearchBar value={searchQuery} onChange={onSearchChange} />
          </div>
        </div>
      </div>
    </motion.header>
  );
}
