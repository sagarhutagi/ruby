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
  Layers,
  Sparkles,
  Sliders,
  Cpu,
  Database,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';
import {
  fetchDocuments,
  uploadDocument,
  deleteDocument,
  fetchDocumentChunks,
  DocumentItem,
  inspectRetrieval,
  fetchRetrievalStats,
  RetrievalInspectResponse,
} from '../services/api';

// Helper for subject fetch
async function getSubjects() {
  const res = await fetch('/api/v1/subjects');
  if (!res.ok) return [];
  return res.json();
}

export const LibraryPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'documents' | 'retrieval'>('documents');

  // Documents state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFormat, setSelectedFormat] = useState<string>('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedDocForChunks, setSelectedDocForChunks] = useState<DocumentItem | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');

  // Retrieval Inspector state
  const [ragQuery, setRagQuery] = useState('');
  const [ragSubjectId, setRagSubjectId] = useState<string>('');
  const [denseWeight, setDenseWeight] = useState<number>(0.5);
  const [sparseWeight, setSparseWeight] = useState<number>(0.5);
  const [topK, setTopK] = useState<number>(5);
  const [inspectResult, setInspectResult] = useState<RetrievalInspectResponse | null>(null);
  const [inspectLoading, setInspectLoading] = useState(false);
  const [inspectError, setInspectError] = useState<string | null>(null);
  const [showContextPreview, setShowContextPreview] = useState(false);

  const { data: documents } = useQuery({
    queryKey: ['documents', searchQuery, selectedFormat],
    queryFn: () => fetchDocuments({ q: searchQuery, file_type: selectedFormat || undefined }),
    refetchInterval: 5000,
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

  const { data: retrievalStats } = useQuery({
    queryKey: ['retrieval-stats'],
    queryFn: fetchRetrievalStats,
    refetchInterval: 10000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['retrieval-stats'] });
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
      queryClient.invalidateQueries({ queryKey: ['retrieval-stats'] });
      setShowUploadModal(false);
    } catch (err: any) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleExecuteRagInspect = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!ragQuery.trim()) return;

    setInspectLoading(true);
    setInspectError(null);
    try {
      const res = await inspectRetrieval({
        query: ragQuery.trim(),
        top_k: topK,
        subject_id: ragSubjectId || undefined,
        dense_weight: denseWeight,
        sparse_weight: sparseWeight,
      });
      setInspectResult(res);
    } catch (err: any) {
      setInspectError(err.message || 'Retrieval failed.');
    } finally {
      setInspectLoading(false);
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
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-emerald-400" />
            Document Intelligence & RAG Engine
          </h2>
          <p className="text-xs text-zinc-400">
            Structure-aware chunking, dense vector similarity (ChromaDB), and BM25 keyword search with Reciprocal Rank Fusion.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeTab === 'documents' && (
            <button
              onClick={() => setShowUploadModal(true)}
              className="flex items-center gap-2 px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
            >
              <Upload className="w-4 h-4" />
              Upload Documents
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-zinc-800 gap-2">
        <button
          onClick={() => setActiveTab('documents')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'documents'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          Repository Documents
        </button>
        <button
          onClick={() => setActiveTab('retrieval')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'retrieval'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          Hybrid RAG Inspector & Diagnostics
        </button>
      </div>

      {/* TAB 1: Documents Management */}
      {activeTab === 'documents' && (
        <div className="space-y-6">
          {/* Filter and Search Bar */}
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents by title or filename..."
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-9 pr-4 py-2 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700"
              />
            </div>
            <select
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-300 focus:outline-none focus:border-zinc-700"
            >
              <option value="">All File Formats</option>
              <option value="pdf">PDF Documents</option>
              <option value="docx">Word (.docx)</option>
              <option value="pptx">PowerPoint (.pptx)</option>
              <option value="xlsx">Spreadsheets (.xlsx, .csv)</option>
              <option value="md">Markdown (.md)</option>
              <option value="txt">Plain Text (.txt)</option>
              <option value="html">HTML</option>
              <option value="epub">EPUB Books</option>
              <option value="png">Images / OCR</option>
            </select>
          </div>

          {/* Documents Grid / Table */}
          <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-xl overflow-hidden">
            {documents && documents.length > 0 ? (
              <div className="divide-y divide-zinc-800/50">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-zinc-900/80 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                        {getFormatIcon(doc.file_type)}
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-xs text-zinc-200">{doc.title}</h4>
                          <span className="uppercase text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                            {doc.file_type}
                          </span>
                          {doc.status === 'indexed' && (
                            <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/50 px-2 py-0.5 rounded-full">
                              <CheckCircle2 className="w-3 h-3" /> Indexed
                            </span>
                          )}
                          {doc.status === 'parsing' && (
                            <span className="flex items-center gap-1 text-[10px] text-amber-400 bg-amber-950/40 border border-amber-800/50 px-2 py-0.5 rounded-full animate-pulse">
                              <Clock className="w-3 h-3" /> Parsing
                            </span>
                          )}
                          {doc.status === 'failed' && (
                            <span className="flex items-center gap-1 text-[10px] text-rose-400 bg-rose-950/40 border border-rose-800/50 px-2 py-0.5 rounded-full">
                              <AlertCircle className="w-3 h-3" /> Failed
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-zinc-500 font-mono">
                          <span>{doc.filename}</span>
                          <span>•</span>
                          <span>{(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
                          {doc.page_count && (
                            <>
                              <span>•</span>
                              <span>{doc.page_count} pages</span>
                            </>
                          )}
                          <span>•</span>
                          <span>{doc.chunk_count} chunks indexed</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <button
                        onClick={() => setSelectedDocForChunks(doc)}
                        className="flex items-center gap-1 px-2.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-xs transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Inspect Chunks
                      </button>
                      <button
                        onClick={() => deleteMutation.mutate(doc.id)}
                        className="p-1.5 text-zinc-500 hover:text-rose-400 rounded transition-colors"
                        title="Delete Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-12 text-center space-y-3">
                <BookOpen className="w-8 h-8 text-zinc-600 mx-auto" />
                <h4 className="text-xs font-medium text-zinc-300">No documents found</h4>
                <p className="text-[11px] text-zinc-500 max-w-sm mx-auto">
                  Upload PDF, Word, PowerPoint, Excel, EPUB, or image documents to index them for hybrid academic retrieval.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Hybrid RAG Inspector */}
      {activeTab === 'retrieval' && (
        <div className="space-y-6">
          {/* Stats Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl space-y-1">
              <span className="text-[11px] text-zinc-400 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-indigo-400" /> Vector Store
              </span>
              <p className="text-sm font-semibold text-zinc-200">
                {retrievalStats?.chroma.collection_name || 'ruby_chunks'}
              </p>
              <span className="text-[10px] text-zinc-500 font-mono">
                {retrievalStats?.chroma.total_chunks ?? 0} vectors indexed
              </span>
            </div>
            <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl space-y-1">
              <span className="text-[11px] text-zinc-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-emerald-400" /> Embedding Provider
              </span>
              <p className="text-sm font-semibold text-zinc-200 capitalize">
                {retrievalStats?.embedding_provider || 'local'}
              </p>
              <span className="text-[10px] text-zinc-500 font-mono">
                {retrievalStats?.embedding_model || 'ruby-local-dense'}
              </span>
            </div>
            <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl space-y-1">
              <span className="text-[11px] text-zinc-400 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-amber-400" /> Vector Dimension
              </span>
              <p className="text-sm font-semibold text-zinc-200">
                {retrievalStats?.dimension || 384} dims
              </p>
              <span className="text-[10px] text-zinc-500">L2 Cosine Space</span>
            </div>
            <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl space-y-1">
              <span className="text-[11px] text-zinc-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-purple-400" /> Hybrid Fusion
              </span>
              <p className="text-sm font-semibold text-zinc-200">RRF (k=60)</p>
              <span className="text-[10px] text-zinc-500">Dense + SQLite FTS5</span>
            </div>
          </div>

          {/* Search Query Form & Controls */}
          <form onSubmit={handleExecuteRagInspect} className="p-4 bg-zinc-900 border border-zinc-800 rounded-xl space-y-4">
            <div className="flex flex-col sm:flex-row items-center gap-2">
              <div className="relative flex-1 w-full">
                <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={ragQuery}
                  onChange={(e) => setRagQuery(e.target.value)}
                  placeholder="Enter academic query (e.g. 'deadlock banker algorithm', 'binary search trees', 'TCP 3-way handshake')..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-9 pr-4 py-2 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <button
                type="submit"
                disabled={inspectLoading || !ragQuery.trim()}
                className="w-full sm:w-auto px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-1.5 shadow-sm"
              >
                {inspectLoading ? 'Executing Hybrid Search...' : 'Run Hybrid Search'}
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Hyperparameter Controls */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-2 border-t border-zinc-800/60 text-xs">
              <div>
                <label className="text-[11px] text-zinc-400 block mb-1">
                  Dense Weight: <span className="font-mono text-indigo-400">{denseWeight.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={denseWeight}
                  onChange={(e) => setDenseWeight(parseFloat(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div>
                <label className="text-[11px] text-zinc-400 block mb-1">
                  Sparse Weight: <span className="font-mono text-emerald-400">{sparseWeight.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={sparseWeight}
                  onChange={(e) => setSparseWeight(parseFloat(e.target.value))}
                  className="w-full accent-emerald-500"
                />
              </div>

              <div>
                <label className="text-[11px] text-zinc-400 block mb-1">Top K Results</label>
                <select
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value, 10))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-zinc-300"
                >
                  <option value={3}>Top 3</option>
                  <option value={5}>Top 5</option>
                  <option value={10}>Top 10</option>
                  <option value={20}>Top 20</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] text-zinc-400 block mb-1">Subject Scope</label>
                <select
                  value={ragSubjectId}
                  onChange={(e) => setRagSubjectId(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-zinc-300"
                >
                  <option value="">All Subjects</option>
                  {subjects?.map((s: any) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </form>

          {inspectError && (
            <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-xs text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{inspectError}</span>
            </div>
          )}

          {/* Inspection Results */}
          {inspectResult && (
            <div className="space-y-4">
              {/* Telemetry Strip */}
              <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-4 font-mono text-[11px]">
                  <span className="text-zinc-400">
                    Dense Latency: <strong className="text-indigo-400">{inspectResult.dense_latency_ms} ms</strong>
                  </span>
                  <span className="text-zinc-400">
                    Sparse Latency: <strong className="text-emerald-400">{inspectResult.sparse_latency_ms} ms</strong>
                  </span>
                  <span className="text-zinc-400">
                    Total Fusion: <strong className="text-amber-400">{inspectResult.total_latency_ms} ms</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-zinc-400">
                    Matched: <strong className="text-zinc-200">{inspectResult.total_found}</strong> chunks
                  </span>
                  <button
                    onClick={() => setShowContextPreview(!showContextPreview)}
                    className="flex items-center gap-1 text-[11px] px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" />
                    {showContextPreview ? 'Hide Prompt Context' : 'View Assembled Prompt Context'}
                  </button>
                </div>
              </div>

              {/* Assembled Context Preview */}
              {showContextPreview && (
                <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-xl space-y-2">
                  <h4 className="text-xs font-semibold text-zinc-300">
                    Assembled Grounding Prompt Context for LLM:
                  </h4>
                  <pre className="text-[11px] font-mono text-zinc-400 bg-zinc-900/60 p-3 rounded-lg border border-zinc-800 whitespace-pre-wrap max-h-60 overflow-y-auto">
                    {inspectResult.sample_context}
                  </pre>
                </div>
              )}

              {/* Fused Chunks List */}
              <div className="space-y-3">
                {inspectResult.fused_chunks.length > 0 ? (
                  inspectResult.fused_chunks.map((chunk, idx) => (
                    <div
                      key={chunk.chunk_id}
                      className="p-4 bg-zinc-900/80 border border-zinc-800 rounded-xl space-y-2 hover:border-zinc-700 transition-colors"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-zinc-800/50 pb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold text-indigo-400">
                            #{idx + 1}
                          </span>
                          <h4 className="text-xs font-semibold text-zinc-200">
                            {chunk.document_title}
                          </h4>
                          {chunk.matched_by === 'both' && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                              Dense + Sparse Match
                            </span>
                          )}
                          {chunk.matched_by === 'dense' && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800/60">
                              Dense Vector Match
                            </span>
                          )}
                          {chunk.matched_by === 'sparse' && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-950 text-amber-400 border border-amber-800/60">
                              BM25 Keyword Match
                            </span>
                          )}
                        </div>

                        {/* Provenance Badges */}
                        <div className="flex items-center gap-2 text-[10px] text-zinc-400 font-mono">
                          {chunk.page_number && chunk.page_number > 0 && (
                            <span className="bg-zinc-800 px-1.5 py-0.5 rounded">Page {chunk.page_number}</span>
                          )}
                          {chunk.slide_number && chunk.slide_number > 0 && (
                            <span className="bg-zinc-800 px-1.5 py-0.5 rounded">Slide {chunk.slide_number}</span>
                          )}
                          {chunk.sheet_name && (
                            <span className="bg-zinc-800 px-1.5 py-0.5 rounded">{chunk.sheet_name} ({chunk.cell_range})</span>
                          )}
                          {chunk.section_heading && (
                            <span className="text-zinc-300 truncate max-w-[200px]">{chunk.section_heading}</span>
                          )}
                        </div>
                      </div>

                      {/* Content */}
                      <p className="text-xs text-zinc-300 leading-relaxed font-sans whitespace-pre-wrap">
                        {chunk.content}
                      </p>

                      {/* Score metrics */}
                      <div className="flex items-center gap-4 text-[10px] text-zinc-500 font-mono pt-1">
                        <span>RRF Score: <strong className="text-zinc-300">{chunk.rrf_score}</strong></span>
                        <span>Dense Similarity: <strong className="text-indigo-400">{(chunk.dense_score * 100).toFixed(1)}%</strong></span>
                        {chunk.sparse_score > 0 && (
                          <span>Sparse BM25: <strong className="text-emerald-400">{(chunk.sparse_score * 100).toFixed(1)}%</strong></span>
                        )}
                        <span>{chunk.token_count} tokens</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-xs text-zinc-400 bg-zinc-900 border border-zinc-800 rounded-xl">
                    No matching chunks found for query &ldquo;{inspectResult.query}&rdquo;.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="font-semibold text-zinc-100 text-sm flex items-center gap-2">
                <Upload className="w-4 h-4 text-emerald-400" />
                Upload Academic Documents
              </h3>
              <button
                onClick={() => setShowUploadModal(false)}
                className="p-1 rounded text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {uploadError && (
              <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-xs text-rose-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Assign Subject (Optional)</label>
                <select
                  value={selectedSubjectId}
                  onChange={(e) => setSelectedSubjectId(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-zinc-700"
                >
                  <option value="">No Subject (General Repository)</option>
                  {subjects?.map((s: any) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>

              <div className="border-2 border-dashed border-zinc-700 hover:border-zinc-500 rounded-xl p-6 text-center space-y-2 bg-zinc-950/40">
                <Upload className="w-8 h-8 text-zinc-500 mx-auto" />
                <p className="text-xs text-zinc-300">Choose one or more academic files</p>
                <p className="text-[10px] text-zinc-500">
                  PDF, DOCX, PPTX, XLSX, CSV, EPUB, TXT, MD, PNG, JPG, TIFF
                </p>
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
                  Uploading, chunking, indexing in FTS5, and generating vector embeddings...
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
