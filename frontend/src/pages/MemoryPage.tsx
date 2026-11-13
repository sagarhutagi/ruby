import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Brain,
  Plus,
  Trash2,
  Edit2,
  Pin,
  PinOff,
  Search,
  Download,
  Upload,
  History,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  X,
  Layers,
} from 'lucide-react';
import {
  fetchMemories,
  createMemory,
  updateMemory,
  deleteMemory,
  togglePinMemory,
  extractMemoryCandidates,
  fetchMemoryAuditTrail,
  exportMemories,
  importMemories,
  MemoryItem,
} from '../services/api';

const MEMORY_TIER_DESCRIPTIONS = {
  working: 'Current active session & short-term context',
  episodic: 'Past discussions, learning difficulties, corrections & study progress',
  semantic: 'Concepts, definitions, formulas & subject facts',
  profile: 'Learning preferences, goals & explanation style',
  procedural: 'Workflows, repeated instructions & problem-solving rules',
};

export const MemoryPage: React.FC = () => {
  const queryClient = useQueryClient();

  // State
  const [activeTab, setActiveTab] = useState<'all' | 'working' | 'episodic' | 'semantic' | 'profile' | 'procedural' | 'audit' | 'extractor'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryItem | null>(null);

  // Form states
  const [formContent, setFormContent] = useState('');
  const [formType, setFormType] = useState('semantic');
  const [formImportance, setFormImportance] = useState(0.7);
  const [formPinned, setFormPinned] = useState(false);

  // Extractor state
  const [extractionText, setExtractionText] = useState('');
  const [extractedCandidates, setExtractedCandidates] = useState<any[]>([]);
  const [extracting, setExtracting] = useState(false);

  // Queries
  const { data: memories } = useQuery({
    queryKey: ['memories', activeTab, searchQuery],
    queryFn: () =>
      fetchMemories({
        memory_type: activeTab !== 'all' && activeTab !== 'audit' && activeTab !== 'extractor' ? activeTab : undefined,
        q: searchQuery || undefined,
      }),
  });

  const { data: auditTrail } = useQuery({
    queryKey: ['memory-audit'],
    queryFn: () => fetchMemoryAuditTrail(),
    enabled: activeTab === 'audit',
  });

  // Calculate tier counts
  const counts = {
    working: memories?.filter((m) => m.memory_type === 'working').length || 0,
    episodic: memories?.filter((m) => m.memory_type === 'episodic').length || 0,
    semantic: memories?.filter((m) => m.memory_type === 'semantic').length || 0,
    profile: memories?.filter((m) => m.memory_type === 'profile').length || 0,
    procedural: memories?.filter((m) => m.memory_type === 'procedural').length || 0,
    total: memories?.length || 0,
  };

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: any) => createMemory(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      setShowCreateModal(false);
      setFormContent('');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateMemory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      setEditingMemory(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });

  const pinMutation = useMutation({
    mutationFn: (id: string) => togglePinMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });

  const handleExport = async () => {
    try {
      const data = await exportMemories();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ruby-memories-export.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const items = JSON.parse(text);
      if (Array.isArray(items)) {
        await importMemories(items);
        queryClient.invalidateQueries({ queryKey: ['memories'] });
        alert(`Successfully imported ${items.length} memories.`);
      }
    } catch (err: any) {
      alert(`Import failed: ${err.message}`);
    }
  };

  const handleRunExtraction = async () => {
    if (!extractionText.trim()) return;
    setExtracting(true);
    try {
      const res = await extractMemoryCandidates(extractionText.trim());
      setExtractedCandidates(res);
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    } finally {
      setExtracting(false);
    }
  };

  const handleApproveCandidate = async (cand: any, idx: number) => {
    await createMemory({
      content: cand.content,
      memory_type: cand.memory_type,
      importance_score: cand.importance_score,
      confidence: cand.confidence,
    });
    setExtractedCandidates((prev) => prev.filter((_, i) => i !== idx));
    queryClient.invalidateQueries({ queryKey: ['memories'] });
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <Brain className="w-5 h-5 text-rose-400" />
            5-Tier Memory Subsystem & Manager
          </h2>
          <p className="text-xs text-zinc-400">
            Explicit, transparent memory governance with candidate extraction, importance scoring, and audit trail.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Add Memory
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-1 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 rounded-lg text-xs transition-colors"
            title="Export memories to JSON"
          >
            <Download className="w-3.5 h-3.5" />
            Export
          </button>
          <label className="flex items-center gap-1 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 rounded-lg text-xs transition-colors cursor-pointer">
            <Upload className="w-3.5 h-3.5" />
            Import
            <input type="file" accept=".json" onChange={handleImport} className="hidden" />
          </label>
        </div>
      </div>

      {/* 5-Tier Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {(['working', 'episodic', 'semantic', 'profile', 'procedural'] as const).map((tier) => (
          <div
            key={tier}
            onClick={() => setActiveTab(tier)}
            className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
              activeTab === tier
                ? 'bg-rose-950/20 border-rose-500/50 shadow-sm'
                : 'bg-zinc-900/40 border-zinc-800/80 hover:bg-zinc-900/70'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">
                {tier}
              </span>
              <span className="text-xs font-mono font-bold text-rose-400">
                {counts[tier]}
              </span>
            </div>
            <p className="text-[10px] text-zinc-500 mt-1 line-clamp-2">
              {MEMORY_TIER_DESCRIPTIONS[tier]}
            </p>
          </div>
        ))}
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-zinc-800 gap-2">
        <button
          onClick={() => setActiveTab('all')}
          className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'all'
              ? 'border-rose-500 text-rose-400'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          All Memories ({counts.total})
        </button>
        <button
          onClick={() => setActiveTab('extractor')}
          className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'extractor'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          Candidate Extractor & Approval
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'audit'
              ? 'border-amber-500 text-amber-400'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          Audit Trail
        </button>
      </div>

      {/* TAB CONTENT: Memories List */}
      {activeTab !== 'audit' && activeTab !== 'extractor' && (
        <div className="space-y-4">
          {/* Search bar */}
          <div className="relative">
            <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search memories by content or concept..."
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-9 pr-4 py-2 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700"
            />
          </div>

          {/* Cards */}
          <div className="space-y-3">
            {memories && memories.length > 0 ? (
              memories.map((mem) => (
                <div
                  key={mem.id}
                  className={`p-4 rounded-xl border transition-all ${
                    mem.is_pinned
                      ? 'bg-zinc-900/90 border-indigo-500/40 shadow-sm'
                      : 'bg-zinc-900/40 border-zinc-800/80 hover:bg-zinc-900/70'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="uppercase text-[10px] font-mono px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300 font-semibold border border-zinc-700/50">
                          {mem.memory_type}
                        </span>
                        {mem.is_pinned && (
                          <span className="flex items-center gap-1 text-[10px] text-indigo-400 bg-indigo-950/60 border border-indigo-800 px-2 py-0.5 rounded-full">
                            <Pin className="w-2.5 h-2.5" /> Pinned
                          </span>
                        )}
                        <span className="text-[10px] font-mono text-zinc-500">
                          Importance: <strong className="text-zinc-300">{(mem.importance_score * 100).toFixed(0)}%</strong>
                        </span>
                        <span className="text-[10px] font-mono text-zinc-500">
                          Confidence: <strong className="text-zinc-300">{(mem.confidence * 100).toFixed(0)}%</strong>
                        </span>
                      </div>

                      <p className="text-xs text-zinc-200 font-sans leading-relaxed">
                        {mem.content}
                      </p>

                      <div className="flex items-center gap-3 text-[10px] font-mono text-zinc-500">
                        <span>Created: {new Date(mem.created_at).toLocaleDateString()}</span>
                        {mem.source_event && <span>Source: {mem.source_event}</span>}
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => pinMutation.mutate(mem.id)}
                        className={`p-1.5 rounded transition-colors ${
                          mem.is_pinned ? 'text-indigo-400 hover:text-indigo-300' : 'text-zinc-500 hover:text-zinc-300'
                        }`}
                        title={mem.is_pinned ? 'Unpin' : 'Pin to top'}
                      >
                        {mem.is_pinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
                      </button>
                      <button
                        onClick={() => setEditingMemory(mem)}
                        className="p-1.5 text-zinc-500 hover:text-zinc-300 rounded transition-colors"
                        title="Edit Memory"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => deleteMutation.mutate(mem.id)}
                        className="p-1.5 text-zinc-500 hover:text-rose-400 rounded transition-colors"
                        title="Delete and purge from indexes"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-12 text-center space-y-3 bg-zinc-900/30 border border-zinc-800 rounded-xl">
                <Brain className="w-8 h-8 text-zinc-600 mx-auto" />
                <h4 className="text-xs font-medium text-zinc-300">No memories found</h4>
                <p className="text-[11px] text-zinc-500 max-w-sm mx-auto">
                  Add learning preferences, problem-solving rules, or run candidate extraction to generate persistent memories.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT: Candidate Extractor */}
      {activeTab === 'extractor' && (
        <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-xl space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              Automated Memory Candidate Extraction & Approval
            </h3>
            <p className="text-xs text-zinc-400 mt-1">
              Extract facts, learning preferences, and mistakes from discussion notes with automated duplicate & contradiction checks.
            </p>
          </div>

          <div className="space-y-3">
            <textarea
              rows={4}
              value={extractionText}
              onChange={(e) => setExtractionText(e.target.value)}
              placeholder="Paste study notes, user instructions, or learning reflections (e.g., 'I prefer LaTeX step-by-step derivations. I struggled with Dijkstra negative edge weights...')..."
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              onClick={handleRunExtraction}
              disabled={extracting || !extractionText.trim()}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors"
            >
              {extracting ? 'Analyzing and Extracting...' : 'Extract Candidates'}
            </button>
          </div>

          {extractedCandidates.length > 0 && (
            <div className="space-y-3 pt-3 border-t border-zinc-800">
              <h4 className="text-xs font-semibold text-zinc-300">
                Extraction Candidates for Review ({extractedCandidates.length}):
              </h4>
              <div className="space-y-2">
                {extractedCandidates.map((cand, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="uppercase text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                          {cand.memory_type}
                        </span>
                        <span className="text-[10px] text-zinc-400 font-mono">
                          Score: {(cand.importance_score * 100).toFixed(0)}%
                        </span>
                        {cand.is_contradiction && (
                          <span className="flex items-center gap-1 text-[10px] text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800">
                            <AlertTriangle className="w-3 h-3" /> Contradiction Detected
                          </span>
                        )}
                        {cand.is_duplicate && (
                          <span className="text-[10px] text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded">
                            Existing Duplicate
                          </span>
                        )}
                      </div>
                      <p className="text-zinc-200">{cand.content}</p>
                    </div>

                    <button
                      onClick={() => handleApproveCandidate(cand, idx)}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium shrink-0 flex items-center gap-1 shadow-sm"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Approve & Save
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Audit Trail */}
      {activeTab === 'audit' && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden divide-y divide-zinc-800">
          <div className="p-4 bg-zinc-950/60 font-semibold text-xs text-zinc-200 flex items-center gap-2">
            <History className="w-4 h-4 text-amber-400" />
            Memory Lifecycle Audit Log
          </div>
          {auditTrail && auditTrail.length > 0 ? (
            auditTrail.map((ev) => (
              <div key={ev.id} className="p-3.5 text-xs flex items-center justify-between gap-4 font-mono">
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                      ev.action === 'created'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : ev.action === 'deleted'
                        ? 'bg-rose-950 text-rose-400 border border-rose-800'
                        : 'bg-indigo-950 text-indigo-400 border border-indigo-800'
                    }`}
                  >
                    {ev.action}
                  </span>
                  <span className="text-zinc-300 font-sans">
                    Memory ID: <strong className="text-zinc-400">{ev.memory_id.slice(0, 8)}...</strong>
                  </span>
                  {ev.details && (
                    <span className="text-zinc-500 text-[11px] truncate max-w-sm">
                      {JSON.stringify(ev.details)}
                    </span>
                  )}
                </div>
                <span className="text-zinc-500 text-[11px] shrink-0">
                  {new Date(ev.created_at).toLocaleString()}
                </span>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-xs text-zinc-500 font-mono">
              No audit records logged yet.
            </div>
          )}
        </div>
      )}

      {/* Create Memory Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="font-semibold text-zinc-100 text-sm flex items-center gap-2">
                <Plus className="w-4 h-4 text-rose-400" />
                Add Persistent Memory
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 rounded text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Category</label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-200"
                >
                  <option value="semantic">Semantic (Fact / Definition)</option>
                  <option value="profile">Profile (Learning Preference / Goal)</option>
                  <option value="episodic">Episodic (Past Session / Mistake)</option>
                  <option value="procedural">Procedural (Workflow / Rule)</option>
                  <option value="working">Working (Current Session Context)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Memory Content</label>
                <textarea
                  rows={3}
                  value={formContent}
                  onChange={(e) => setFormContent(e.target.value)}
                  placeholder="Enter memory statement..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-rose-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Importance Score: <span className="font-mono text-rose-400">{formImportance.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={formImportance}
                  onChange={(e) => setFormImportance(parseFloat(e.target.value))}
                  className="w-full accent-rose-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="pin-check"
                  checked={formPinned}
                  onChange={(e) => setFormPinned(e.target.checked)}
                  className="rounded bg-zinc-950 border-zinc-800"
                />
                <label htmlFor="pin-check" className="text-xs text-zinc-300">
                  Pin to top of context
                </label>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 rounded text-xs text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!formContent.trim()}
                  onClick={() =>
                    createMutation.mutate({
                      content: formContent.trim(),
                      memory_type: formType,
                      importance_score: formImportance,
                      is_pinned: formPinned,
                    })
                  }
                  className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded text-xs font-medium transition-colors"
                >
                  Save Memory
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Memory Modal */}
      {editingMemory && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="font-semibold text-zinc-100 text-sm flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-indigo-400" />
                Edit Memory
              </h3>
              <button
                onClick={() => setEditingMemory(null)}
                className="p-1 rounded text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Content</label>
                <textarea
                  rows={3}
                  value={editingMemory.content}
                  onChange={(e) =>
                    setEditingMemory({ ...editingMemory, content: e.target.value })
                  }
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Importance Score: <span className="font-mono text-indigo-400">{editingMemory.importance_score.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={editingMemory.importance_score}
                  onChange={(e) =>
                    setEditingMemory({
                      ...editingMemory,
                      importance_score: parseFloat(e.target.value),
                    })
                  }
                  className="w-full accent-indigo-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingMemory(null)}
                  className="px-3 py-1.5 rounded text-xs text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() =>
                    updateMutation.mutate({
                      id: editingMemory.id,
                      data: {
                        content: editingMemory.content,
                        importance_score: editingMemory.importance_score,
                      },
                    })
                  }
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition-colors"
                >
                  Update Memory
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
