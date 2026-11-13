import React from 'react';
import { BookOpen, Upload, Search, Filter } from 'lucide-react';

export const LibraryPage: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-emerald-400" />
            Document Library
          </h2>
          <p className="text-xs text-zinc-400">
            Import, inspect, and organize academic papers, textbooks, and notes.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm">
            <Upload className="w-4 h-4" />
            Upload Resources
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search documents by title, contents, or tags..."
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-9 pr-4 py-2.5 text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-700"
          />
        </div>
        <button className="flex items-center gap-2 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-zinc-300 hover:bg-zinc-800 transition-colors">
          <Filter className="w-4 h-4" />
          Filter
        </button>
      </div>

      <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/30 p-12 text-center">
        <div className="w-12 h-12 rounded-xl bg-zinc-800/50 flex items-center justify-center mx-auto text-zinc-400 mb-3">
          <BookOpen className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-medium text-zinc-200">No documents in library</h3>
        <p className="text-xs text-zinc-400 max-w-sm mx-auto mt-1">
          Drag and drop PDF, DOCX, PPTX, XLSX, EPUB, or Markdown files here to ingest them into Ruby.
        </p>
      </div>
    </div>
  );
};
