import React from 'react';
import { GraduationCap, Layers, Terminal, Clock } from 'lucide-react';

export const StudyPage: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="border-b border-zinc-800 pb-4">
        <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
          <GraduationCap className="w-5 h-5 text-amber-400" />
          Study & Revision Hub
        </h2>
        <p className="text-xs text-zinc-400">
          Spaced repetition flashcards (FSRS), interactive tutors, and timed examination simulations.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">FSRS Flashcards</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Free Spaced Repetition Scheduler algorithm with personalized retention tracking.
          </p>
          <div className="pt-2">
            <button className="w-full py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg transition-colors">
              Start Due Reviews (0 due)
            </button>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">Mock Examination</span>
            <Clock className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Custom exams with time limits, negative marking, and post-exam error analysis.
          </p>
          <div className="pt-2">
            <button className="w-full py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg transition-colors">
              Configure Mock Exam
            </button>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">Sandboxed DSA Tutor</span>
            <Terminal className="w-4 h-4 text-rose-400" />
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Step-by-step algorithmic dry-runs with restricted, timeout-bounded execution.
          </p>
          <div className="pt-2">
            <button className="w-full py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg transition-colors">
              Open DSA Workspace
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
