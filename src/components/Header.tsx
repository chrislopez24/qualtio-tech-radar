'use client';

import { Github, Radar } from 'lucide-react';
import { ModeToggle } from './ModeToggle';
import { SearchBar } from './SearchBar';
import type { Mode } from '@/lib/types';

interface HeaderProps {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  searchQuery: string;
  onSearchChange: (value: string) => void;
}

export function Header({ 
  mode, 
  onModeChange, 
  searchQuery, 
  onSearchChange 
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 glassmorphism border-b">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
              <Radar className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">Qualtio Tech Radar</h1>
              <p className="text-xs text-muted-foreground">Technology trends tracker</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <SearchBar value={searchQuery} onChange={onSearchChange} />
            <ModeToggle mode={mode} onModeChange={onModeChange} />
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-md hover:bg-muted transition-colors"
            >
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}