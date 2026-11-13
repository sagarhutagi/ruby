import React from 'react';
import { MessageSquare, Sparkles, Send } from 'lucide-react';

export const ChatPage: React.FC = () => {
  return (
    <div className="h-full flex flex-col max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-indigo-400" />
            Academic Chat
          </h2>
          <p className="text-xs text-zinc-400">
            Grounded reasoning over imported documents and personal memory.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-2 py-1 bg-zinc-900 border border-zinc-800 text-zinc-300 rounded">
            Mode: Resource-grounded
          </span>
        </div>
      </div>

      <div className="flex-1 rounded-xl bg-zinc-900/40 border border-zinc-800/80 p-6 flex flex-col items-center justify-center text-center">
        <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-3">
          <Sparkles className="w-6 h-6" />
        </div>
        <h3 className="font-medium text-zinc-200">Start an Academic Discussion</h3>
        <p className="text-xs text-zinc-400 max-w-sm mt-1">
          Ask questions against your imported textbooks, research papers, lecture notes, or formulate derivations.
        </p>
      </div>

      <div className="relative">
        <input
          type="text"
          placeholder="Ask a question or request a derivation (e.g., 'Explain Dijkstra algorithm with step-by-step example')..."
          className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500/50 pr-12 shadow-sm"
        />
        <button className="absolute right-2.5 top-2.5 p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors">
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
