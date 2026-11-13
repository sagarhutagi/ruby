import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FolderTree, Plus, Book, Trash2, Folder } from 'lucide-react';

interface SubjectItem {
  id: string;
  name: string;
  description?: string;
  color: string;
  icon?: string;
  collection_count: number;
  document_count: number;
}

export const SubjectsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState('#3b82f6');
  const [error, setError] = useState<string | null>(null);

  const { data: subjects, isLoading } = useQuery<SubjectItem[]>({
    queryKey: ['subjects'],
    queryFn: async () => {
      const res = await fetch('/api/v1/subjects');
      if (!res.ok) throw new Error('Failed to fetch subjects');
      return res.json();
    },
  });

  const createMutation = useMutation({
    mutationFn: async (payload: { name: string; description?: string; color: string }) => {
      const res = await fetch('/api/v1/subjects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to create subject');
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subjects'] });
      setShowAddModal(false);
      setName('');
      setDescription('');
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`/api/v1/subjects/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete subject');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subjects'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    createMutation.mutate({ name: name.trim(), description: description.trim() || undefined, color });
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <FolderTree className="w-5 h-5 text-indigo-400" />
            Academic Subjects & Domains
          </h2>
          <p className="text-xs text-zinc-400">
            Structure your knowledge base, textbooks, and practice materials into domains.
          </p>
        </div>
        <button
          onClick={() => {
            setError(null);
            setShowAddModal(true);
          }}
          className="flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Add Subject
        </button>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-zinc-400">Loading subjects...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {subjects?.map((subj) => (
            <div
              key={subj.id}
              className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center mb-3 text-white"
                    style={{
                      backgroundColor: `${subj.color}20`,
                      borderColor: `${subj.color}40`,
                      borderWidth: 1,
                    }}
                  >
                    <Book className="w-5 h-5" style={{ color: subj.color }} />
                  </div>
                  <button
                    onClick={() => {
                      if (confirm(`Delete subject '${subj.name}'?`)) {
                        deleteMutation.mutate(subj.id);
                      }
                    }}
                    className="p-1 text-zinc-400 hover:text-rose-400 rounded transition-colors"
                    title="Delete Subject"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <h3 className="font-semibold text-sm text-zinc-100">{subj.name}</h3>
                <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                  {subj.description || 'No description provided.'}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-zinc-800/60 flex items-center justify-between text-[11px] text-zinc-400 font-mono">
                <span className="flex items-center gap-1">
                  <Folder className="w-3 h-3" />
                  {subj.collection_count} collections
                </span>
                <span>{subj.document_count} resources</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Subject Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="font-semibold text-zinc-100 text-sm flex items-center gap-2">
                <Plus className="w-4 h-4 text-indigo-400" />
                Create Academic Subject
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-zinc-400 hover:text-zinc-200 text-sm"
              >
                ✕
              </button>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1 font-medium">Subject Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Artificial Intelligence"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1 font-medium">Description</label>
                <textarea
                  rows={3}
                  placeholder="Core syllabus and focus areas..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-200 focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1 font-medium">Theme Color</label>
                <div className="flex items-center gap-3">
                  <input
                    type="color"
                    value={color}
                    onChange={(e) => setColor(e.target.value)}
                    className="w-8 h-8 rounded border-0 bg-transparent cursor-pointer"
                  />
                  <span className="font-mono text-zinc-400">{color}</span>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
                >
                  {createMutation.isPending ? 'Saving...' : 'Create Subject'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
