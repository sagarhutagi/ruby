import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  FolderTree,
  Network,
  Brain,
  GraduationCap,
  BarChart3,
  Cpu,
  Settings,
} from 'lucide-react';
import { HealthStatus } from '../../types';

interface SidebarProps {
  health?: HealthStatus;
  isLoadingHealth: boolean;
}

const NAV_ITEMS = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'AI Chat', path: '/chat', icon: MessageSquare },
  { name: 'Library', path: '/library', icon: BookOpen },
  { name: 'Subjects', path: '/subjects', icon: FolderTree },
  { name: 'Knowledge Graph', path: '/graph', icon: Network },
  { name: 'Memory Manager', path: '/memory', icon: Brain },
  { name: 'Study & Revision', path: '/study', icon: GraduationCap },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'AI Providers', path: '/providers', icon: Cpu },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({ health, isLoadingHealth }) => {
  const isHealthy = health?.status === 'healthy';

  return (
    <aside className="w-64 h-screen bg-zinc-900/90 border-r border-zinc-800/80 flex flex-col justify-between select-none">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 gap-3 border-b border-zinc-800/60">
          <div className="w-8 h-8 rounded-lg bg-rose-600/20 border border-rose-500/40 flex items-center justify-center text-rose-400 font-bold text-lg shadow-sm">
            R
          </div>
          <div>
            <h1 className="font-semibold text-zinc-100 text-sm tracking-wide">RUBY</h1>
            <p className="text-[11px] text-zinc-400 font-mono">Academic AI</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-zinc-800 text-zinc-100 shadow-sm border border-zinc-700/50'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Backend Health Status Badge */}
      <div className="p-4 border-t border-zinc-800/60 bg-zinc-950/40">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isLoadingHealth
                  ? 'bg-amber-400 animate-pulse'
                  : isHealthy
                  ? 'bg-emerald-500 ring-2 ring-emerald-500/20'
                  : 'bg-rose-500 ring-2 ring-rose-500/20'
              }`}
            />
            <span className="font-mono text-[11px] text-zinc-300">
              {isLoadingHealth ? 'Connecting...' : isHealthy ? 'Core Online' : 'Core Disconnected'}
            </span>
          </div>
          <span className="text-[10px] font-mono text-zinc-400">
            {health?.version ? `v${health.version}` : 'v0.1.0'}
          </span>
        </div>
      </div>
    </aside>
  );
};
