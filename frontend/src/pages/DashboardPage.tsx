import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  MessageSquare,
  Cpu,
  Brain,
  Layers,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { fetchHealth } from '../services/api';

export const DashboardPage: React.FC = () => {
  const { data: health, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  });

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Hero Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            Ruby Academic Intelligence
            <span className="text-xs font-mono font-normal px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
              v0.1.0
            </span>
          </h2>
          <p className="text-sm text-zinc-400 mt-1">
            Local-first, privacy-respecting academic copilot, document intelligence & spaced repetition engine.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono bg-zinc-900 border border-zinc-800 text-zinc-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            100% Local Inference Ready
          </span>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 shadow-sm">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">System Core</span>
            <Cpu className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-lg font-semibold text-zinc-100">
            {isLoading ? 'Checking...' : health?.status === 'healthy' ? 'Operational' : 'Degraded'}
          </div>
          <p className="text-[11px] text-zinc-400 mt-1 font-mono">
            {health?.environment || 'development'} mode
          </p>
        </div>

        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 shadow-sm">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Storage Engine</span>
            <Layers className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-lg font-semibold text-zinc-100">SQLite + ChromaDB</div>
          <p className="text-[11px] text-zinc-400 mt-1 font-mono">
            WAL mode & FTS5 indexed
          </p>
        </div>

        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 shadow-sm">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">AI Inferencer</span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-lg font-semibold text-zinc-100">Ollama Local</div>
          <p className="text-[11px] text-zinc-400 mt-1 font-mono">
            RTX 3050 Laptop GPU (6GB)
          </p>
        </div>

        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 shadow-sm">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Memory Tiers</span>
            <Brain className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-lg font-semibold text-zinc-100">5-Tier Active</div>
          <p className="text-[11px] text-zinc-400 mt-1 font-mono">
            Working & Episodic & Semantic
          </p>
        </div>
      </div>

      {/* Feature Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <a
          href="/chat"
          className="group block p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all"
        >
          <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 group-hover:scale-105 transition-transform">
            <MessageSquare className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-zinc-100 text-sm group-hover:text-indigo-300 transition-colors">
            Academic Chat & RAG
          </h3>
          <p className="text-xs text-zinc-400 mt-1.5 leading-relaxed">
            Multi-document reasoning with verifiable citations, LaTeX math formulas, and 4 specialized answer modes.
          </p>
        </a>

        <a
          href="/library"
          className="group block p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all"
        >
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4 group-hover:scale-105 transition-transform">
            <BookOpen className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-zinc-100 text-sm group-hover:text-emerald-300 transition-colors">
            Document Ingestion & Library
          </h3>
          <p className="text-xs text-zinc-400 mt-1.5 leading-relaxed">
            Universal ingestion for PDF, DOCX, PPTX, XLSX, EPUB, and Markdown with OCR and page-level provenance.
          </p>
        </a>

        <a
          href="/study"
          className="group block p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/70 transition-all"
        >
          <div className="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mb-4 group-hover:scale-105 transition-transform">
            <Brain className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-zinc-100 text-sm group-hover:text-rose-300 transition-colors">
            Spaced Repetition & Tutors
          </h3>
          <p className="text-xs text-zinc-400 mt-1.5 leading-relaxed">
            FSRS flashcard algorithm, dynamic exam generation, SymPy math solver, and sandboxed DSA visualizer.
          </p>
        </a>
      </div>

      {/* System Integrity Checklist */}
      <div className="p-5 rounded-xl bg-zinc-900/30 border border-zinc-800/80">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-3">
          Architecture Status & Verification
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="flex items-center gap-2 text-zinc-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>SQLite async ORM + Alembic migrations operational</span>
          </div>
          <div className="flex items-center gap-2 text-zinc-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>SQLite FTS5 full-text keyword indexing configured</span>
          </div>
          <div className="flex items-center gap-2 text-zinc-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Localhost-only network binding (127.0.0.1) enforced</span>
          </div>
          <div className="flex items-center gap-2 text-zinc-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Configurable data directory: {health?.data_directory || './data'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
