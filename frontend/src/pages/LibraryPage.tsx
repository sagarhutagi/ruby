import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BookOpen,
  Upload,
  Search,
  Trash2,
  FileText,
  FileSpreadsheet,
  Presentation,
  Image as ImageIcon,
  CheckCircle2,
  Clock,
  AlertCircle,
  Eye,
  X,
  FileCode,
} from 'lucide-react';
import {
  fetchDocuments,
  uploadDocument,
  deleteDocument,
  fetchDocumentChunks,
  DocumentItem,
} from '../services/api';

// Helper for subject fetch
async function getSubjects() {
  const res = await fetch('/api/v1/subjects');
  if (!res.ok) return [];
  return res.json();
}

export const LibraryPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFormat, setSelectedFormat] = useState<string>('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedDocForChunks, setSelectedDocForChunks] = useState<DocumentItem | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', searchQuery, selectedFormat],
    queryFn: () => fetchDocuments({ q: searchQuery, file_type: selectedFormat || undefined }),
    refetchInterval: 5000, // Poll every 5s to update indexing progress
  });

  const { data: subjects } = useQuery({
    queryKey: ['subjects'],
    queryFn: getSubjects,
  });

  const { data: chunks, isLoading: loadingChunks } = useQuery({
    queryKey: ['chunks', selectedDocForChunks?.id],
    queryFn: () => (selectedDocForChunks ? fetchDocumentChunks(selectedDocForChunks.id) : []),
    enabled: !!selectedDocForChunks,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadError(null);
    try {
      for (let i = 0; i < files.length; i++) {
        await uploadDocument(files[i], selectedSubjectId || undefined);
      }
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setShowUploadModal(false);
    } catch (err: any) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const getFormatIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'pdf':
        return <FileText className="w-5 h-5 text-rose-400" />;
      case 'docx':
      case 'doc':
        return <FileText className="w-5 h-5 text-indigo-400" />;
      case 'pptx':
      case 'ppt':
        return <Presentation className="w-5 h-5 text-amber-400" />;
      case 'xlsx':
      case 'csv':
        return <FileSpreadsheet className="w-5 h-5 text-emerald-400" />;
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'webp':
        return <ImageIcon className="w-5 h-5 text-purple-400" />;
      default:
        return <FileCode className="w-5 h-5 text-zinc-400" />;
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-emerald-400" />
            Document Library & Ingestion Engine
          </h2>
          <p className="text-xs text-zinc-400">
            Universal multi-format parser (PDF, DOCX, PPTX, XLSX, EPUB, Images/OCR) with page-level provenance.
          </p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
        >
          <Upload className="w-4 h-4" />
          Upload Documents
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by title or filename..."
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-9 pr-4 py-2 text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-700"
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
            className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-300 focus:outline-none"
          >
            <option value="">All Formats</option>
            <option value="pdf">PDF (.pdf)</option>
            <option value="docx">Word (.docx)</option>
            <option value="pptx">PowerPoint (.pptx)</option>
            <option value="xlsx">Excel / CSV</option>
            <option value="epub">EPUB Books</option>
            <option value="md">Markdown / Text</option>
          </select>
        </div>
      </div>

      {/* Documents List */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-zinc-400">Loading library...</div>
      ) : documents && documents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 transition-all flex flex-col justify-between space-y-3"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-zinc-800/60 border border-zinc-700/40">
                      {getFormatIcon(doc.file_type)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-xs text-zinc-100 truncate max-w-[200px]" title={doc.title}>
                        {doc.title}
                      </h3>
                      <p className="text-[11px] text-zinc-400 truncate max-w-[200px]" title={doc.filename}>
                        {doc.filename}
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700/40">
                    {doc.file_type}
                  </span>
                </div>

                <div className="mt-3 flex items-center justify-between text-[11px] text-zinc-400 font-mono">
                  <span>{(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
                  {doc.page_count !== undefined && doc.page_count !== null && (
                    <span>{doc.page_count} pages / slides</span>
                  )}
                  <span>{doc.chunk_count} chunks</span>
                </div>
              </div>

              {/* Status and Action Buttons */}
              <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px]">
                  {doc.status === 'indexed' && (
                    <span className="text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Indexed
                    </span>
                  )}
                  {doc.status === 'parsing' && (
                    <span className="text-indigo-400 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 animate-spin" /> Ingesting...
                    </span>
                  )}
                  {doc.status === 'pending' && (
                    <span className="text-amber-400 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> Queued
                    </span>
                  )}
                  {doc.status === 'failed' && (
                    <span className="text-rose-400 flex items-center gap-1" title={doc.error_message || ''}>
                      <AlertCircle className="w-3.5 h-3.5" /> Failed
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedDocForChunks(doc)}
                    className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors"
                    title="Inspect Extracted Chunks"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete document '${doc.title}'?`)) {
                        deleteMutation.mutate(doc.id);
                      }
                    }}
                    className="p-1.5 text-zinc-400 hover:text-rose-400 hover:bg-zinc-800 rounded transition-colors"
                    title="Delete Document"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/30 p-12 text-center">
          <div className="w-12 h-12 rounded-xl bg-zinc-800/50 flex items-center justify-center mx-auto text-zinc-400 mb-3">
            <BookOpen className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-medium text-zinc-200">No documents found</h3>
          <p className="text-xs text-zinc-400 max-w-sm mx-auto mt-1">
            Upload PDF, DOCX, PPTX, XLSX, EPUB, or Markdown files to begin.
          </p>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="font-semibold text-zinc-100 text-sm flex items-center gap-2">
                <Upload className="w-4 h-4 text-emerald-400" />
                Ingest Academic Documents
              </h3>
              <button onClick={() => setShowUploadModal(false)} className="text-zinc-400 hover:text-zinc-200 text-sm">
                ✕
              </button>
            </div>

            {uploadError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {uploadError}
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1 font-medium">Assign Subject (Optional)</label>
                <select
                  value={selectedSubjectId}
                  onChange={(e) => setSelectedSubjectId(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-200 focus:outline-none"
                >
                  <option value="">No Subject</option>
                  {subjects?.map((s: any) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 mb-1 font-medium">Select Files</label>
                <input
                  type="file"
                  multiple
                  disabled={uploading}
                  onChange={handleFileUpload}
                  className="w-full text-xs text-zinc-400 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-zinc-800 file:text-zinc-200 hover:file:bg-zinc-700 cursor-pointer"
                />
              </div>

              {uploading && (
                <div className="pt-2 text-center text-xs text-indigo-400 animate-pulse">
                  Uploading and extracting document structure...
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Chunks Inspector Drawer / Modal */}
      {selectedDocForChunks && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-3xl w-full max-h-[85vh] flex flex-col p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div>
                <h3 className="font-semibold text-zinc-100 text-sm">
                  Document Chunks: {selectedDocForChunks.title}
                </h3>
                <p className="text-[11px] text-zinc-400 font-mono">
                  {selectedDocForChunks.chunk_count} total chunks with exact source provenance
                </p>
              </div>
              <button
                onClick={() => setSelectedDocForChunks(null)}
                className="p-1 rounded text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {loadingChunks ? (
                <div className="p-8 text-center text-xs text-zinc-400">Loading chunks...</div>
              ) : chunks && chunks.length > 0 ? (
                chunks.map((c) => (
                  <div key={c.id} className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800/80 text-xs space-y-2">
                    <div className="flex items-center justify-between text-[11px] font-mono text-indigo-300">
                      <span>Chunk #{c.chunk_index}</span>
                      <div className="flex items-center gap-2 text-zinc-400">
                        {c.page_number && <span className="bg-zinc-800/60 px-1.5 py-0.5 rounded">Page {c.page_number}</span>}
                        {c.slide_number && <span className="bg-zinc-800/60 px-1.5 py-0.5 rounded">Slide {c.slide_number}</span>}
                        {c.sheet_name && <span className="bg-zinc-800/60 px-1.5 py-0.5 rounded">{c.sheet_name} ({c.cell_range})</span>}
                        {c.section_heading && <span className="text-zinc-300 truncate max-w-[200px]">{c.section_heading}</span>}
                        <span>{c.token_count} tokens</span>
                      </div>
                    </div>
                    <pre className="font-sans text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed bg-zinc-900/40 p-2.5 rounded border border-zinc-850">
                      {c.content}
                    </pre>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs text-zinc-400">No chunks indexed for this document.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
