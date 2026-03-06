'use client';

import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MagnifyingGlass, X, Command } from '@phosphor-icons/react';
import { focusShortcutTarget } from '@/lib/search-shortcut';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function SearchBar({ value, onChange, placeholder = 'Search technologies...' }: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        focusShortcutTarget(inputRef.current);
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="relative group">
      {/* Glow effect on focus */}
      <motion.div
        className="absolute -inset-0.5 rounded-xl bg-gradient-to-r from-[#00d4ff]/20 to-[#ff006e]/20 opacity-0 group-focus-within:opacity-100 transition-opacity duration-500 blur-sm"
      />
      
      <div className="relative flex items-center">
        <MagnifyingGlass 
          className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary group-focus-within:text-accent-cyan transition-colors" 
          weight="duotone" 
        />
        
        <input
          ref={inputRef}
          type="text"
          aria-label="Search technologies"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full pl-11 pr-24 py-2.5 bg-bg-secondary/80 border border-border-subtle rounded-xl
                     text-sm text-white placeholder:text-text-tertiary
                     focus:outline-none focus:border-accent-cyan/30 focus:bg-bg-tertiary
                     transition-all duration-300
                     font-body"
        />
        
        {/* Keyboard shortcut hint */}
        <AnimatePresence>
          {!value && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="absolute right-3 flex items-center gap-1 px-2 py-1 rounded-md bg-bg-tertiary border border-border-subtle"
            >
              <Command className="w-3 h-3 text-text-tertiary" weight="duotone" />
              <span className="text-[10px] font-mono text-text-tertiary uppercase">K</span>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Clear button */}
        <AnimatePresence>
          {value && (
            <motion.button
              type="button"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              onClick={() => onChange('')}
              className="absolute right-3 p-1 rounded-md text-text-tertiary hover:text-white hover:bg-white/10 transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              aria-label="Clear search"
            >
              <X className="w-4 h-4" weight="bold" />
            </motion.button>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
