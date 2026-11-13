import React from 'react';
import { ShieldCheck, HardDrive, PanelLeft } from 'lucide-react';
import { HealthStatus } from '../../types';

interface HeaderProps {
  health?: HealthStatus;
  isSidebarOpen?: boolean;
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ health, isSidebarOpen, onToggleSidebar }) => {
  return (
    <header className="h-14 border-b border-[#2e2e2e] bg-[#212121]/90 backdrop-blur px-4 flex items-center justify-between shrink-0 select-none">
      <div className="flex items-center gap-3">
        {onToggleSidebar && !isSidebarOpen && (
          <button
            onClick={onToggleSidebar}
            className="p-1.5 text-[#b4b4b4] hover:text-white hover:bg-[#2f2f2f] rounded-lg transition-colors cursor-pointer"
            title="Open sidebar"
          >
            <PanelLeft className="w-4 h-4" />
          </button>
        )}
        <span className="text-[11px] font-mono uppercase tracking-wider text-[#a1a1aa] bg-[#2a2a2a] px-2.5 py-1 rounded border border-[#383838]">
          Local Environment
        </span>
        <span className="text-xs text-[#8e8e8e] font-mono hidden md:inline">
          127.0.0.1:8000
        </span>
      </div>

      <div className="flex items-center gap-3">
        {/* Local-First Privacy Badge */}
        <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2.5 py-1 rounded-md">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span className="font-medium text-[11px]">Local First & Private</span>
        </div>

        {/* Database state */}
        <div className="flex items-center gap-1.5 text-xs text-[#a1a1aa] bg-[#2a2a2a] border border-[#383838] px-2.5 py-1 rounded-md">
          <HardDrive className="w-3.5 h-3.5 text-[#8e8e8e]" />
          <span className="font-mono text-[11px]">
            {health?.database_connected ? 'SQLite Connected' : 'DB Offline'}
          </span>
        </div>
      </div>
    </header>
  );
};
