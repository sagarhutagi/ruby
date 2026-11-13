import React from 'react';
import { Brain, ShieldCheck } from 'lucide-react';

const MEMORY_TIERS = [
  { name: 'Working Memory', count: 0, desc: 'Current active session context' },
  { name: 'Episodic Memory', count: 0, desc: 'Past learning sessions & corrections' },
  { name: 'Semantic Memory', count: 0, desc: 'Concepts, definitions & formulas' },
  { name: 'Profile Memory', count: 0, desc: 'Learning pace & preferences' },
  { name: 'Procedural Memory', count: 0, desc: 'Preferred workflows & styles' },
];

export const MemoryPage: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <Brain className="w-5 h-5 text-rose-400" />
            Memory Manager
          </h2>
          <p className="text-xs text-zinc-400">
            Transparent, user-controlled 5-tier memory subsystem with audit history.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-lg">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          User Governed & Deletable
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {MEMORY_TIERS.map((tier) => (
          <div key={tier.name} className="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
            <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">{tier.name}</div>
            <div className="text-lg font-bold text-zinc-100 mt-1">{tier.count}</div>
            <div className="text-[10px] text-zinc-400 mt-0.5">{tier.desc}</div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/30 p-12 text-center">
        <div className="w-12 h-12 rounded-xl bg-zinc-800/50 flex items-center justify-center mx-auto text-zinc-400 mb-3">
          <Brain className="w-6 h-6 text-rose-400" />
        </div>
        <h3 className="text-sm font-medium text-zinc-200">No memories extracted yet</h3>
        <p className="text-xs text-zinc-400 max-w-sm mx-auto mt-1">
          As you interact with Ruby, candidate facts and learning preferences are extracted, scored, and listed here for your approval.
        </p>
      </div>
    </div>
  );
};
