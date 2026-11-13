import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  MessageSquare,
  Sparkles,
  Send,
  Plus,
  Trash2,
  Edit2,
  Download,
  Shield,
  Globe,
  Shuffle,
  Microscope,
  Square,
  Search,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  X,
} from 'lucide-react';
import {
  fetchConversations,
  createConversation,
  fetchConversation,
  updateConversation,
  deleteConversation,
  exportConversationMarkdown,
  streamChat,
  ConversationItem,
  ChatMessageItem,
} from '../services/api';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

// Helper for subjects
async function getSubjects() {
  const res = await fetch('/api/v1/subjects');
  if (!res.ok) return [];
  return res.json();
}

async function getProviders() {
  const res = await fetch('/api/v1/providers');
  if (!res.ok) return [];
  return res.json();
}

export const ChatPage: React.FC = () => {
  const queryClient = useQueryClient();

  // State
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [searchConvQuery, setSearchConvQuery] = useState('');
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [chatMode, setChatMode] = useState<string>('resource-grounded');
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingSources, setStreamingSources] = useState<any[]>([]);
  const [abortStream, setAbortStream] = useState<(() => void) | null>(null);

  // Modals & Panels
  const [editingTitleId, setEditingTitleId] = useState<string | null>(null);
  const [editingTitleText, setEditingTitleText] = useState('');
  const [selectedCitationChunk, setSelectedCitationChunk] = useState<any | null>(null);
  const [expandedDiagnostics, setExpandedDiagnostics] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Queries
  const { data: conversations, refetch: refetchConversations } = useQuery({
    queryKey: ['conversations', searchConvQuery, selectedSubjectId],
    queryFn: () =>
      fetchConversations({
        q: searchConvQuery || undefined,
        subject_id: selectedSubjectId || undefined,
      }),
  });

  const { data: currentConv, refetch: refetchCurrentConv } = useQuery({
    queryKey: ['conversation', activeConvId],
    queryFn: () => (activeConvId ? fetchConversation(activeConvId) : null),
    enabled: !!activeConvId,
  });

  const { data: subjects } = useQuery({
    queryKey: ['subjects'],
    queryFn: getSubjects,
  });

  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: getProviders,
  });

  // Auto-select first conversation if none selected
  useEffect(() => {
    if (!activeConvId && conversations && conversations.length > 0) {
      setActiveConvId(conversations[0].id);
    }
  }, [conversations, activeConvId]);

  // Scroll to bottom on new messages or streaming
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConv?.messages, streamingText]);

  // Mutations
  const newConversationMutation = useMutation({
    mutationFn: () =>
      createConversation({
        title: 'New Conversation',
        subject_id: selectedSubjectId || undefined,
      }),
    onSuccess: (newConv) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setActiveConvId(newConv.id);
    },
  });

  const deleteConvMutation = useMutation({
    mutationFn: (id: string) => deleteConversation(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (activeConvId === deletedId) {
        setActiveConvId(null);
      }
    },
  });

  const updateTitleMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      updateConversation(id, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      queryClient.invalidateQueries({ queryKey: ['conversation', activeConvId] });
      setEditingTitleId(null);
    },
  });

  // Active Provider Info
  const activeProvider = providers?.find((p: any) => p.is_default) || providers?.[0];

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isStreaming) return;

    let targetConvId = activeConvId;
    if (!targetConvId) {
      const created = await createConversation({
        title: inputText.slice(0, 30),
        subject_id: selectedSubjectId || undefined,
      });
      targetConvId = created.id;
      setActiveConvId(created.id);
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    }

    const messageContent = inputText.trim();
    setInputText('');
    setIsStreaming(true);
    setStreamingText('');
    setStreamingSources([]);

    const cancel = streamChat(
      {
        conversation_id: targetConvId,
        content: messageContent,
        mode: chatMode,
        subject_id: selectedSubjectId || undefined,
      },
      {
        onSources: (chunks) => {
          setStreamingSources(chunks);
        },
        onToken: (token) => {
          setStreamingText((prev) => prev + token);
        },
        onDone: () => {
          setIsStreaming(false);
          setStreamingText('');
          setStreamingSources([]);
          refetchCurrentConv();
          refetchConversations();
        },
        onError: (err) => {
          setIsStreaming(false);
          setStreamingText((prev) => prev + `\n\n[Error: ${err}]`);
          refetchCurrentConv();
        },
      }
    );

    setAbortStream(() => cancel);
  };

  const handleStopStream = () => {
    if (abortStream) {
      abortStream();
      setAbortStream(null);
    }
    setIsStreaming(false);
    refetchCurrentConv();
  };

  const handleExportMarkdown = async () => {
    if (!activeConvId) return;
    try {
      const md = await exportConversationMarkdown(activeConvId);
      const blob = new Blob([md], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ruby-chat-${activeConvId.slice(0, 8)}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  return (
    <div className="h-[calc(100vh-5rem)] flex gap-4 max-w-7xl mx-auto">
      {/* Conversations Left Sidebar */}
      <div className="w-64 bg-zinc-900/60 border border-zinc-800 rounded-xl flex flex-col overflow-hidden shrink-0">
        {/* Header with New Chat Button */}
        <div className="p-3 border-b border-zinc-800 space-y-2">
          <button
            onClick={() => newConversationMutation.mutate()}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Conversation
          </button>
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={searchConvQuery}
              onChange={(e) => setSearchConvQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full bg-zinc-950 border border-zinc-850 rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-zinc-700"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto divide-y divide-zinc-850/60">
          {conversations && conversations.length > 0 ? (
            conversations.map((c: ConversationItem) => {
              const isActive = c.id === activeConvId;
              const isEditing = editingTitleId === c.id;

              return (
                <div
                  key={c.id}
                  onClick={() => !isEditing && setActiveConvId(c.id)}
                  className={`p-3 cursor-pointer transition-colors group flex items-start justify-between gap-2 ${
                    isActive ? 'bg-zinc-800/80 text-zinc-100' : 'hover:bg-zinc-855/50 text-zinc-400'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    {isEditing ? (
                      <input
                        type="text"
                        autoFocus
                        value={editingTitleText}
                        onChange={(e) => setEditingTitleText(e.target.value)}
                        onBlur={() => {
                          if (editingTitleText.trim()) {
                            updateTitleMutation.mutate({ id: c.id, title: editingTitleText.trim() });
                          } else {
                            setEditingTitleId(null);
                          }
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            updateTitleMutation.mutate({ id: c.id, title: editingTitleText.trim() });
                          } else if (e.key === 'Escape') {
                            setEditingTitleId(null);
                          }
                        }}
                        className="w-full bg-zinc-950 border border-indigo-500 rounded px-1.5 py-0.5 text-xs text-zinc-100"
                      />
                    ) : (
                      <>
                        <h4 className="text-xs font-medium truncate">{c.title}</h4>
                        <p className="text-[10px] text-zinc-500 truncate mt-0.5">
                          {c.last_message_preview || 'No messages yet'}
                        </p>
                      </>
                    )}
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingTitleId(c.id);
                        setEditingTitleText(c.title);
                      }}
                      className="p-1 text-zinc-400 hover:text-zinc-200 rounded"
                      title="Rename conversation"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConvMutation.mutate(c.id);
                      }}
                      className="p-1 text-zinc-400 hover:text-rose-400 rounded"
                      title="Delete conversation"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="p-6 text-center text-[11px] text-zinc-500">
              No conversations found.
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 bg-zinc-900/50 border border-zinc-800 rounded-xl flex flex-col overflow-hidden">
        {/* Chat Header */}
        <div className="px-4 py-3 border-b border-zinc-800 flex flex-wrap items-center justify-between gap-3 bg-zinc-900/80">
          <div className="flex items-center gap-3">
            <MessageSquare className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-xs text-zinc-200">
              {currentConv?.title || 'Academic Intelligence Chat'}
            </h3>
            {activeProvider && (
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                  activeProvider.provider_type === 'ollama'
                    ? 'bg-emerald-950/60 border-emerald-800/60 text-emerald-300'
                    : 'bg-amber-950/60 border-amber-800/60 text-amber-300'
                }`}
              >
                <Cpu className="w-3 h-3" />
                {activeProvider.model_name} (
                {activeProvider.provider_type === 'ollama' ? 'Local' : 'Cloud'})
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Subject Selector */}
            <select
              value={selectedSubjectId}
              onChange={(e) => setSelectedSubjectId(e.target.value)}
              className="bg-zinc-950 border border-zinc-800 rounded-lg px-2.5 py-1 text-[11px] text-zinc-300 focus:outline-none focus:border-zinc-700"
            >
              <option value="">All Subjects Context</option>
              {subjects?.map((s: any) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>

            {/* Mode Pills */}
            <div className="flex bg-zinc-950 p-0.5 rounded-lg border border-zinc-800">
              <button
                onClick={() => setChatMode('resource-grounded')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                  chatMode === 'resource-grounded'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
                title="Strictly grounded on uploaded documents with citations"
              >
                <Shield className="w-3 h-3" />
                Grounded
              </button>
              <button
                onClick={() => setChatMode('general')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                  chatMode === 'general'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
                title="General knowledge model reasoning without document context"
              >
                <Globe className="w-3 h-3" />
                General
              </button>
              <button
                onClick={() => setChatMode('hybrid')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                  chatMode === 'hybrid'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
                title="Document evidence supplemented by general knowledge"
              >
                <Shuffle className="w-3 h-3" />
                Hybrid
              </button>
              <button
                onClick={() => setChatMode('research')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                  chatMode === 'research'
                    ? 'bg-amber-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
                title="Cross-document comparative analysis and synthesis"
              >
                <Microscope className="w-3 h-3" />
                Research
              </button>
            </div>

            {/* Export Button */}
            {currentConv && (
              <button
                onClick={handleExportMarkdown}
                className="p-1.5 text-zinc-400 hover:text-zinc-200 rounded border border-zinc-800 hover:border-zinc-700 bg-zinc-950 transition-colors"
                title="Export conversation as Markdown"
              >
                <Download className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {currentConv && currentConv.messages && currentConv.messages.length > 0 ? (
            currentConv.messages.map((msg: ChatMessageItem) => {
              const isUser = msg.role === 'user';
              const isDiagExpanded = !!expandedDiagnostics[msg.id];

              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-3xl rounded-xl p-4 shadow-sm space-y-2 ${
                      isUser
                        ? 'bg-indigo-600/90 text-white border border-indigo-500/50'
                        : 'bg-zinc-950/80 text-zinc-200 border border-zinc-800'
                    }`}
                  >
                    {/* Header info */}
                    {!isUser && (
                      <div className="flex items-center justify-between border-b border-zinc-850 pb-2 mb-2 text-[10px] text-zinc-400 font-mono">
                        <div className="flex items-center gap-2">
                          <span className="capitalize">{msg.mode}</span>
                          <span>•</span>
                          <span>{msg.model_used || 'AI'}</span>
                        </div>
                        {msg.diagnostics?.total_latency_ms && (
                          <div className="flex items-center gap-2">
                            <span>{msg.diagnostics.total_latency_ms} ms</span>
                            <button
                              onClick={() =>
                                setExpandedDiagnostics((prev) => ({
                                  ...prev,
                                  [msg.id]: !prev[msg.id],
                                }))
                              }
                              className="text-zinc-400 hover:text-zinc-200 flex items-center"
                            >
                              {isDiagExpanded ? (
                                <ChevronUp className="w-3 h-3" />
                              ) : (
                                <ChevronDown className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Content */}
                    {isUser ? (
                      <p className="text-xs font-sans whitespace-pre-wrap leading-relaxed">
                        {msg.content}
                      </p>
                    ) : (
                      <MarkdownRenderer
                        content={msg.content}
                        onCitationClick={(tag) => {
                          const matched = msg.citations?.find((c: any) => c.raw_tag === tag);
                          if (matched) {
                            setSelectedCitationChunk(matched);
                          }
                        }}
                      />
                    )}

                    {/* Citations Panel */}
                    {!isUser && msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-zinc-850 space-y-1.5">
                        <span className="text-[10px] font-semibold text-zinc-400 flex items-center gap-1">
                          <BookOpen className="w-3 h-3 text-indigo-400" />
                          Verified Sources & Provenance ({msg.citations.length}):
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((c: any, cIdx: number) => (
                            <button
                              key={cIdx}
                              onClick={() => setSelectedCitationChunk(c)}
                              className={`flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded border transition-colors ${
                                c.is_verified
                                  ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300 hover:bg-emerald-900'
                                  : 'bg-rose-950/60 border-rose-800 text-rose-300 hover:bg-rose-900'
                              }`}
                            >
                              {c.is_verified ? (
                                <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                              ) : (
                                <AlertTriangle className="w-2.5 h-2.5 text-rose-400" />
                              )}
                              <span>
                                {c.document_title || 'Document'}
                                {c.page_number ? ` (p. ${c.page_number})` : ''}
                                {c.slide_number ? ` (slide ${c.slide_number})` : ''}
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Diagnostics Details */}
                    {isDiagExpanded && msg.diagnostics && (
                      <div className="mt-2 p-2.5 bg-zinc-900/90 rounded border border-zinc-800 text-[10px] font-mono text-zinc-400 space-y-1">
                        <div>Retrieval Latency: {msg.diagnostics.retrieval_latency_ms} ms</div>
                        <div>Generation Latency: {msg.diagnostics.generation_latency_ms} ms</div>
                        <div>Total Latency: {msg.diagnostics.total_latency_ms} ms</div>
                        <div>Tokens: ~{msg.tokens_used}</div>
                        {msg.diagnostics.grounding && (
                          <div>
                            Grounding Status:{' '}
                            <strong
                              className={
                                msg.diagnostics.grounding.is_grounded
                                  ? 'text-emerald-400'
                                  : 'text-amber-400'
                              }
                            >
                              {msg.diagnostics.grounding.message}
                            </strong>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-3">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-medium text-zinc-200">
                Academic Knowledge Copilot
              </h3>
              <p className="text-xs text-zinc-400 max-w-md leading-relaxed">
                Select an answer mode and ask any question against your textbooks, notes, and research.
                Grounded mode guarantees citations with exact page numbers.
              </p>
            </div>
          )}

          {/* Real-time Streaming Message Card */}
          {isStreaming && (
            <div className="flex flex-col items-start">
              <div className="max-w-3xl rounded-xl p-4 bg-zinc-950/90 border border-indigo-500/50 shadow-lg space-y-2 text-zinc-200">
                <div className="flex items-center justify-between border-b border-zinc-850 pb-2 mb-2 text-[10px] text-indigo-400 font-mono">
                  <div className="flex items-center gap-1.5 animate-pulse">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Streaming response...</span>
                  </div>
                  {streamingSources.length > 0 && (
                    <span className="text-zinc-400">
                      Found {streamingSources.length} source chunks
                    </span>
                  )}
                </div>

                {streamingText ? (
                  <MarkdownRenderer content={streamingText} />
                ) : (
                  <div className="text-xs text-zinc-500 animate-pulse">
                    Retrieving evidence & formulating academic answer...
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Controls */}
        <div className="p-3 border-t border-zinc-800 bg-zinc-900/80 space-y-2">
          <form onSubmit={handleSendMessage} className="relative flex items-center">
            <textarea
              rows={2}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder={`Ask an academic question in ${chatMode} mode... (Shift+Enter for newline)`}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500/60 pr-20 resize-none shadow-sm"
            />
            <div className="absolute right-3 flex items-center gap-2">
              {isStreaming ? (
                <button
                  type="button"
                  onClick={handleStopStream}
                  className="flex items-center gap-1 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
                >
                  <Square className="w-3 h-3 fill-current" />
                  Stop
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!inputText.trim()}
                  className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg transition-colors shadow-sm"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </form>
        </div>
      </div>

      {/* Citation Inspector Modal */}
      {selectedCitationChunk && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-lg w-full p-5 shadow-2xl space-y-3">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <h3 className="font-semibold text-zinc-100 text-xs flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-indigo-400" />
                Source Citation Provenance
              </h3>
              <button
                onClick={() => setSelectedCitationChunk(null)}
                className="p-1 rounded text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-850 space-y-1 text-[11px] font-mono text-zinc-400">
                <div>Document: <strong className="text-zinc-200">{selectedCitationChunk.document_title}</strong></div>
                {selectedCitationChunk.page_number && (
                  <div>Page Number: <strong className="text-zinc-200">{selectedCitationChunk.page_number}</strong></div>
                )}
                {selectedCitationChunk.slide_number && (
                  <div>Slide Number: <strong className="text-zinc-200">{selectedCitationChunk.slide_number}</strong></div>
                )}
                {selectedCitationChunk.sheet_name && (
                  <div>Spreadsheet: <strong className="text-zinc-200">{selectedCitationChunk.sheet_name} ({selectedCitationChunk.cell_range})</strong></div>
                )}
                {selectedCitationChunk.section_heading && (
                  <div>Section Heading: <strong className="text-zinc-200">{selectedCitationChunk.section_heading}</strong></div>
                )}
                <div>Verification Status: <strong className={selectedCitationChunk.is_verified ? 'text-emerald-400' : 'text-rose-400'}>{selectedCitationChunk.is_verified ? 'Verified in Source Chunks' : 'Unverified Citation'}</strong></div>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] text-zinc-500 font-mono">Raw Citation Tag:</span>
                <p className="font-mono text-xs text-indigo-300 bg-zinc-950 p-2 rounded border border-zinc-850">
                  {selectedCitationChunk.raw_tag}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
