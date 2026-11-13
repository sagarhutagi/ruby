import React from 'react';
import { FolderTree, Plus, Book, Binary, Network, Cpu, Terminal } from 'lucide-react';

const SEEDED_SUBJECTS = [
  { name: 'Mathematics', desc: 'Calculus, Linear Algebra, Discrete Math, Probability & Statistics', color: '#3b82f6', icon: Book },
  { name: 'Data Structures & Algorithms', desc: 'Arrays, Trees, Graphs, Dynamic Programming, Complexity', color: '#10b981', icon: Binary },
  { name: 'Computer Networks', desc: 'OSI/TCP-IP models, Routing, Congestion Control, Protocols', color: '#f59e0b', icon: Network },
  { name: 'Digital Logic & Computer Design', desc: 'Boolean Algebra, Logic Gates, K-Maps, Sequential Circuits', color: '#8b5cf6', icon: Cpu },
  { name: 'Operating Systems', desc: 'Processes, Threads, Scheduling, Virtual Memory, File Systems', color: '#ec4899', icon: Terminal },
];

export const SubjectsPage: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <FolderTree className="w-5 h-5 text-indigo-400" />
            Academic Subjects
          </h2>
          <p className="text-xs text-zinc-400">
            Organize resources, flashcards, and notes into structured learning domains.
          </p>
        </div>
        <button className="flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm">
          <Plus className="w-4 h-4" />
          Add Subject
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SEEDED_SUBJECTS.map((subj) => {
          const Icon = subj.icon;
          return (
            <div
              key={subj.name}
              className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700/80 transition-all flex flex-col justify-between"
            >
              <div>
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center mb-3 text-white"
                  style={{ backgroundColor: `${subj.color}20`, borderColor: `${subj.color}40`, borderWidth: 1 }}
                >
                  <Icon className="w-5 h-5" style={{ color: subj.color }} />
                </div>
                <h3 className="font-semibold text-sm text-zinc-100">{subj.name}</h3>
                <p className="text-xs text-zinc-400 mt-1 leading-relaxed">{subj.desc}</p>
              </div>
              <div className="mt-4 pt-3 border-t border-zinc-800/60 flex items-center justify-between text-[11px] text-zinc-400">
                <span>0 collections</span>
                <span>0 resources</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
