import React from 'react';
import { ShieldCheck, HardDrive } from 'lucide-react';
import { HealthStatus } from '../../types';

interface HeaderProps {
  health?: HealthStatus;
}

export const Header: React.FC<HeaderProps> = ({ health }) => {
  return (
    <header className="h-16 border-b border-zinc-800/80 bg-zinc-900/40 backdrop-blur px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 bg-zinc-800/60 px-2.5 py-1 rounded border border-zinc-700/40">
          Local Environment
        </span>
        <span className="text-xs text-zinc-400 font-mono hidden md:inline">
          127.0.0.1:8000
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* Local-First Privacy Badge */}
        <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-md">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span className="font-medium text-[11px]">Local First & Private</span>
        </div>

        {/* Database state */}
        <div className="flex items-center gap-1.5 text-xs text-zinc-400 bg-zinc-800/60 border border-zinc-700/40 px-2.5 py-1 rounded-md">
          <HardDrive className="w-3.5 h-3.5 text-zinc-400" />
          <span className="font-mono text-[11px]">
            {health?.database_connected ? 'SQLite Connected' : 'DB Offline'}
          </span>
        </div>
      </div>
    </header>
  );
};
