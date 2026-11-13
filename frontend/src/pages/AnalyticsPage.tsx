import React from 'react';
import { BarChart3, Activity, HardDrive, Cpu } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="border-b border-zinc-800 pb-4">
        <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-indigo-400" />
          Analytics & System Resources
        </h2>
        <p className="text-xs text-zinc-400">
          Real-time hardware utilization, token usage telemetry, and study efficiency metrics.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Host Memory</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-zinc-100">24 GB System RAM</div>
          <p className="text-xs text-zinc-400 mt-1">Available for large context operations</p>
        </div>

        <div className="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">GPU Dedicated VRAM</span>
            <Cpu className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-xl font-bold text-zinc-100">6,144 MB (RTX 3050)</div>
          <p className="text-xs text-zinc-400 mt-1">Optimized for 4-bit 3B–8B models</p>
        </div>

        <div className="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Storage NVMe</span>
            <HardDrive className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-zinc-100">512 GB Fast NVMe</div>
          <p className="text-xs text-zinc-400 mt-1">ChromaDB + SQLite storage</p>
        </div>
      </div>
    </div>
  );
};
