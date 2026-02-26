'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { MagnifyingGlass, X, Command } from '@phosphor-icons/react';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function SearchBar({ value, onChange, placeholder = 'Search technologies...' }: SearchBarProps) {
  return (
    <div className="relative group">
      {/* Glow effect on focus */}
      <motion.div
        className="absolute -inset-0.5 rounded-xl bg-gradient-to-r from-[#00d4ff]/20 to-[#ff006e]/20 opacity-0 group-focus-within:opacity-100 transition-opacity duration-500 blur-sm"
      />
      
      <div className="relative flex items-center">
        <MagnifyingGlass 
          className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6a6a7a] group-focus-within:text-[#00d4ff] transition-colors" 
          weight="duotone" 
        />
        
        <input
          type="text"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full pl-11 pr-24 py-2.5 bg-[#12121a]/80 border border-[#ffffff08] rounded-xl
                     text-sm text-white placeholder:text-[#6a6a7a]
                     focus:outline-none focus:border-[#00d4ff]/30 focus:bg-[#1a1a24]
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
              className="absolute right-3 flex items-center gap-1 px-2 py-1 rounded-md bg-[#1a1a24] border border-[#ffffff08]"
            >
              <Command className="w-3 h-3 text-[#6a6a7a]" weight="duotone" />
              <span className="text-[10px] font-mono text-[#6a6a7a] uppercase">K</span>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Clear button */}
        <AnimatePresence>
          {value && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              onClick={() => onChange('')}
              className="absolute right-3 p-1 rounded-md text-[#6a6a7a] hover:text-white hover:bg-white/10 transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              <X className="w-4 h-4" weight="bold" />
            </motion.button>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
