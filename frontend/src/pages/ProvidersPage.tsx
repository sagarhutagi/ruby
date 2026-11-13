import React from 'react';
import { Cpu, Plus, Shield } from 'lucide-react';

export const ProvidersPage: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" />
            AI Providers & Inference
          </h2>
          <p className="text-xs text-zinc-400">
            Configure local Ollama, cloud APIs (OpenAI, Gemini, Claude, OpenRouter), and model routing.
          </p>
        </div>
        <button className="flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm">
          <Plus className="w-4 h-4" />
          Add Provider
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Ollama Local Card */}
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <h3 className="font-semibold text-sm text-zinc-100">Ollama (Local)</h3>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Default Provider
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono">http://127.0.0.1:11434</p>
          <div className="pt-2 flex items-center justify-between border-t border-zinc-800/60 text-xs">
            <span className="text-zinc-400">Active model: llama3.2:latest</span>
            <button className="text-xs text-indigo-400 hover:text-indigo-300">Test Connection</button>
          </div>
        </div>

        {/* Security Notice */}
        <div className="p-5 rounded-xl bg-zinc-900/20 border border-dashed border-zinc-800 space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium text-zinc-300">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span>Encrypted Secret Storage</span>
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            API keys are securely sealed in the OS keyring (Linux Secret Service) or AES-GCM encrypted storage. Credentials are never stored in plaintext SQLite or returned in frontend responses.
          </p>
        </div>
      </div>
    </div>
  );
};
