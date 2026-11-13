import React from 'react';
import { Settings, Folder, Lock } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { fetchHealth } from '../services/api';

export const SettingsPage: React.FC = () => {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="border-b border-zinc-800 pb-4">
        <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
          <Settings className="w-5 h-5 text-zinc-400" />
          Application Settings
        </h2>
        <p className="text-xs text-zinc-400">
          Storage directories, Obsidian vault integration, and privacy preferences.
        </p>
      </div>

      <div className="space-y-4">
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
            <Folder className="w-4 h-4 text-indigo-400" />
            Storage & Data Location
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5 font-medium">
              Data Directory Path
            </label>
            <input
              type="text"
              readOnly
              value={health?.data_directory || './data'}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs font-mono text-zinc-300"
            />
            <p className="text-[11px] text-zinc-400 mt-1">
              Houses SQLite database, ChromaDB vector store, and raw document storage.
            </p>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
            <Lock className="w-4 h-4 text-emerald-400" />
            Security & Binding Configuration
          </div>
          <div className="flex items-center justify-between text-xs text-zinc-300">
            <span>Enforce Localhost Binding (127.0.0.1)</span>
            <span className="font-mono text-emerald-400">Enabled</span>
          </div>
          <div className="flex items-center justify-between text-xs text-zinc-300 border-t border-zinc-800/60 pt-3">
            <span>Explicit Cloud Transfer Consent Required</span>
            <span className="font-mono text-emerald-400">Enabled</span>
          </div>
        </div>
      </div>
    </div>
  );
};
