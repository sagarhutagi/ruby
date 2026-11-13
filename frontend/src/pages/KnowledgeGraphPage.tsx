import React from 'react';
import { Network, ZoomIn, ZoomOut, Filter, Compass } from 'lucide-react';

export const KnowledgeGraphPage: React.FC = () => {
  return (
    <div className="h-full flex flex-col space-y-4">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <Network className="w-5 h-5 text-indigo-400" />
            Knowledge Graph
          </h2>
          <p className="text-xs text-zinc-400">
            Interactive relational map of subjects, concepts, formulas, and prerequisites.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200">
            <ZoomOut className="w-4 h-4" />
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-zinc-300">
            <Filter className="w-3.5 h-3.5" />
            Filter Nodes
          </button>
        </div>
      </div>

      <div className="flex-1 rounded-xl bg-zinc-900/30 border border-zinc-800/80 relative flex items-center justify-center overflow-hidden">
        <div className="text-center">
          <div className="w-12 h-12 rounded-xl bg-zinc-800/40 flex items-center justify-center mx-auto text-zinc-400 mb-3">
            <Compass className="w-6 h-6 text-indigo-400" />
          </div>
          <h3 className="text-sm font-medium text-zinc-200">Concept Map Explorer</h3>
          <p className="text-xs text-zinc-400 max-w-sm mt-1">
            Relationships are automatically derived and user-editable using SQLite graph links and React Flow.
          </p>
        </div>
      </div>
    </div>
  );
};
