import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles,
  ArrowUp,
  Square,
  Shield,
  Globe,
  Shuffle,
  Microscope,
  BookOpen,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  X,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  Download,
  Plus,
  Layers,
  GraduationCap,
  Calculator,
  Compass,
} from 'lucide-react';
import {
  fetchConversation,
  createConversation,
  exportConversationMarkdown,
  streamChat,
  ChatMessageItem,
} from '../services/api';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

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

const PROMPT_SUGGESTIONS = [
  {
    icon: BookOpen,
    title: 'Summarize Lecture Notes',
    prompt: 'Synthesize the main themes, core formulas, and key takeaways from my uploaded lecture slides.',
  },
  {
    icon: Compass,
    title: 'Explain Step-by-Step',
    prompt: 'Explain virtual memory paging, page tables, and TLB translation with an intuitive real-world analogy.',
  },
  {
    icon: GraduationCap,
    title: 'Generate FSRS Flashcards',
    prompt: 'Create 5 spaced repetition flashcards testing key concepts for my upcoming Operating Systems exam.',
  },
  {
    icon: Calculator,
    title: 'Math & Algorithm Sandbox',
    prompt: 'Compute the derivative and integral of x^3 * sin(x) and trace the execution of binary search.',
  },
];

export const ChatPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeConvId = searchParams.get('c');

  // Chat Configuration State
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [chatMode, setChatMode] = useState<string>('resource-grounded');
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingSources, setStreamingSources] = useState<any[]>([]);
  const [abortStream, setAbortStream] = useState<(() => void) | null>(null);

  // Modals & Panels
  const [selectedCitationChunk, setSelectedCitationChunk] = useState<any | null>(null);
  const [expandedDiagnostics, setExpandedDiagnostics] = useState<Record<string, boolean>>({});
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [modelPickerOpen, setModelPickerOpen] = useState(false);
  const [subjectPickerOpen, setSubjectPickerOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Queries
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

  const activeProvider = providers?.find((p: any) => p.is_default) || providers?.[0];

  // Auto-resize textarea like ChatGPT
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputText]);

  // Scroll to bottom on new messages or streaming
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConv?.messages, streamingText]);

  const handleSendMessage = async (customPrompt?: string) => {
    const textToSend = (customPrompt || inputText).trim();
    if (!textToSend || isStreaming) return;

    let targetConvId = activeConvId;
    if (!targetConvId) {
      const created = await createConversation({
        title: textToSend.slice(0, 36),
        subject_id: selectedSubjectId || undefined,
      });
      targetConvId = created.id;
      setSearchParams({ c: created.id });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    }

    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setIsStreaming(true);
    setStreamingText('');
    setStreamingSources([]);

    const cancel = streamChat(
      {
        conversation_id: targetConvId,
        content: textToSend,
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
          queryClient.invalidateQueries({ queryKey: ['conversations'] });
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

  const handleCopyMessage = (id: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedMessageId(id);
    setTimeout(() => setCopiedMessageId(null), 2000);
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

  const selectedSubject = subjects?.find((s: any) => s.id === selectedSubjectId);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#212121] text-[#ececec] relative overflow-hidden select-text">
      {/* ChatGPT Top Header Bar */}
      <header className="h-14 border-b border-[#2e2e2e] bg-[#212121]/80 backdrop-blur-md px-4 flex items-center justify-between shrink-0 z-20">
        {/* Model Selector Dropdown (ChatGPT style) */}
        <div className="relative">
          <button
            onClick={() => setModelPickerOpen((prev) => !prev)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl hover:bg-[#2f2f2f] text-sm font-medium text-[#ececec] transition-colors cursor-pointer"
          >
            <span className="font-semibold tracking-tight text-white">
              {activeProvider?.model_name || 'Ruby 4o'}
            </span>
            {activeProvider && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#2e2e2e] text-[#a1a1aa] border border-[#3e3e3e]">
                {activeProvider.provider_type === 'ollama' ? 'Local' : 'Cloud'}
              </span>
            )}
            <ChevronDown className="w-3.5 h-3.5 text-[#8e8e8e]" />
          </button>

          {modelPickerOpen && (
            <div className="absolute left-0 top-full mt-1.5 w-72 rounded-2xl bg-[#2a2a2a] border border-[#383838] shadow-2xl p-2 z-50 text-xs">
              <div className="px-3 py-1.5 text-[11px] font-medium text-[#8e8e8e] uppercase tracking-wider">
                Active Provider & Model
              </div>
              <div className="space-y-1 mt-1">
                {providers?.map((p: any) => (
                  <div
                    key={p.id}
                    onClick={() => setModelPickerOpen(false)}
                    className={`flex items-center justify-between p-2.5 rounded-xl cursor-pointer transition-colors ${
                      p.is_default
                        ? 'bg-[#383838] text-white'
                        : 'hover:bg-[#333333] text-[#b4b4b4]'
                    }`}
                  >
                    <div>
                      <div className="font-medium text-sm text-[#ececec]">{p.model_name}</div>
                      <div className="text-[11px] text-[#8e8e8e] capitalize">
                        {p.provider_type} {p.provider_type === 'ollama' && '• Zero Cloud Leakage'}
                      </div>
                    </div>
                    {p.is_default && <Check className="w-4 h-4 text-emerald-400" />}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Center / Right: Mode Switcher Pills & Context Filter */}
        <div className="flex items-center gap-2">
          {/* Subject Filter Pill */}
          <div className="relative">
            <button
              onClick={() => setSubjectPickerOpen((prev) => !prev)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[#383838] bg-[#282828] hover:bg-[#303030] text-xs text-[#b4b4b4] hover:text-white transition-colors cursor-pointer"
            >
              <Layers className="w-3.5 h-3.5 text-[#8e8e8e]" />
              <span className="max-w-[120px] truncate">
                {selectedSubject ? selectedSubject.name : 'All Subjects'}
              </span>
              <ChevronDown className="w-3 h-3 text-[#8e8e8e]" />
            </button>

            {subjectPickerOpen && (
              <div className="absolute right-0 top-full mt-1.5 w-56 rounded-xl bg-[#2a2a2a] border border-[#383838] shadow-2xl p-1.5 z-50 text-xs">
                <button
                  onClick={() => {
                    setSelectedSubjectId('');
                    setSubjectPickerOpen(false);
                  }}
                  className={`w-full text-left p-2 rounded-lg transition-colors ${
                    !selectedSubjectId ? 'bg-[#383838] text-white' : 'text-[#b4b4b4] hover:bg-[#333]'
                  }`}
                >
                  All Course Context
                </button>
                {subjects?.map((s: any) => (
                  <button
                    key={s.id}
                    onClick={() => {
                      setSelectedSubjectId(s.id);
                      setSubjectPickerOpen(false);
                    }}
                    className={`w-full text-left p-2 rounded-lg truncate transition-colors ${
                      selectedSubjectId === s.id
                        ? 'bg-[#383838] text-white'
                        : 'text-[#b4b4b4] hover:bg-[#333]'
                    }`}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Mode Switcher Group (ChatGPT Search / Deep Research Pill style) */}
          <div className="hidden sm:flex items-center bg-[#282828] p-0.5 rounded-xl border border-[#383838]">
            <button
              onClick={() => setChatMode('resource-grounded')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                chatMode === 'resource-grounded'
                  ? 'bg-[#3e3e3e] text-white shadow-sm'
                  : 'text-[#b4b4b4] hover:text-white'
              }`}
              title="Grounded in uploaded documents with citations"
            >
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>Grounded</span>
            </button>
            <button
              onClick={() => setChatMode('general')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                chatMode === 'general'
                  ? 'bg-[#3e3e3e] text-white shadow-sm'
                  : 'text-[#b4b4b4] hover:text-white'
              }`}
              title="General knowledge model reasoning"
            >
              <Globe className="w-3.5 h-3.5 text-blue-400" />
              <span>General</span>
            </button>
            <button
              onClick={() => setChatMode('hybrid')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                chatMode === 'hybrid'
                  ? 'bg-[#3e3e3e] text-white shadow-sm'
                  : 'text-[#b4b4b4] hover:text-white'
              }`}
              title="Blended evidence and reasoning"
            >
              <Shuffle className="w-3.5 h-3.5 text-purple-400" />
              <span>Hybrid</span>
            </button>
            <button
              onClick={() => setChatMode('research')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                chatMode === 'research'
                  ? 'bg-[#3e3e3e] text-white shadow-sm'
                  : 'text-[#b4b4b4] hover:text-white'
              }`}
              title="Comparative cross-document synthesis"
            >
              <Microscope className="w-3.5 h-3.5 text-amber-400" />
              <span>Research</span>
            </button>
          </div>

          {/* Export Chat */}
          {currentConv && (
            <button
              onClick={handleExportMarkdown}
              className="p-1.5 text-[#b4b4b4] hover:text-white rounded-lg hover:bg-[#2f2f2f] transition-colors"
              title="Export conversation as Markdown"
            >
              <Download className="w-4 h-4" />
            </button>
          )}
        </div>
      </header>

      {/* Main Conversation Stream */}
      <div className="flex-1 overflow-y-auto">
        {currentConv && currentConv.messages && currentConv.messages.length > 0 ? (
          <div className="max-w-3xl mx-auto w-full px-4 pt-6 pb-40 space-y-7">
            {currentConv.messages.map((msg: ChatMessageItem) => {
              const isUser = msg.role === 'user';
              const isDiagExpanded = !!expandedDiagnostics[msg.id];

              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  {isUser ? (
                    /* User Message Bubble - Sleek ChatGPT Right Bubble */
                    <div className="max-w-[80%] rounded-[24px] bg-[#2f2f2f] text-[#ececec] px-5 py-3 text-[15px] leading-relaxed shadow-sm">
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  ) : (
                    /* Assistant Message - Clean Full Width Typography with Avatar */
                    <div className="w-full space-y-3">
                      {/* Avatar & Model Header */}
                      <div className="flex items-center gap-2.5 text-xs text-[#8e8e8e]">
                        <div className="w-7 h-7 rounded-full bg-[#343541] border border-[#444] flex items-center justify-center text-rose-400 font-bold text-xs shadow-sm">
                          <Sparkles className="w-4 h-4 text-rose-400" />
                        </div>
                        <span className="font-medium text-white text-sm">Ruby</span>
                        <span>•</span>
                        <span className="capitalize">{msg.mode || 'Grounded'}</span>
                        {msg.diagnostics?.total_latency_ms && (
                          <>
                            <span>•</span>
                            <span className="font-mono text-[11px]">
                              {msg.diagnostics.total_latency_ms}ms
                            </span>
                          </>
                        )}
                      </div>

                      {/* Content */}
                      <div className="pl-9 text-[15px] leading-7 text-[#ececec]">
                        <MarkdownRenderer
                          content={msg.content}
                          onCitationClick={(tag) => {
                            const matched = msg.citations?.find((c: any) => c.raw_tag === tag);
                            if (matched) {
                              setSelectedCitationChunk(matched);
                            }
                          }}
                        />

                        {/* Verified Sources Drawer (ChatGPT Web Search & NotebookLM style) */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-4 pt-3 border-t border-[#2e2e2e] space-y-2">
                            <span className="text-xs font-medium text-[#8e8e8e] flex items-center gap-1.5">
                              <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
                              Verified Sources ({msg.citations.length})
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {msg.citations.map((c: any, cIdx: number) => (
                                <button
                                  key={cIdx}
                                  onClick={() => setSelectedCitationChunk(c)}
                                  className={`flex items-center gap-1.5 text-xs font-mono px-3 py-1 rounded-full border transition-colors cursor-pointer shadow-sm ${
                                    c.is_verified
                                      ? 'bg-[#1e293b]/70 border-[#334155] text-[#93c5fd] hover:bg-[#334155]'
                                      : 'bg-[#3b1219]/70 border-[#5c1d24] text-[#fca5a5] hover:bg-[#5c1d24]'
                                  }`}
                                >
                                  {c.is_verified ? (
                                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                                  ) : (
                                    <AlertTriangle className="w-3 h-3 text-rose-400" />
                                  )}
                                  <span className="font-sans truncate max-w-[200px]">
                                    {c.document_title || 'Document'}
                                    {c.page_number ? ` (p. ${c.page_number})` : ''}
                                  </span>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Diagnostics Detail Box (Collapsible) */}
                        {isDiagExpanded && msg.diagnostics && (
                          <div className="mt-3 p-3 bg-[#191919] rounded-xl border border-[#333] text-xs font-mono text-[#a1a1aa] space-y-1">
                            <div>Retrieval Latency: {msg.diagnostics.retrieval_latency_ms} ms</div>
                            <div>Generation Latency: {msg.diagnostics.generation_latency_ms} ms</div>
                            <div>Total Latency: {msg.diagnostics.total_latency_ms} ms</div>
                            <div>Tokens Used: ~{msg.tokens_used}</div>
                            {msg.diagnostics.grounding && (
                              <div>
                                Grounding Verification:{' '}
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

                        {/* Bottom Action Bar (ChatGPT Style) */}
                        <div className="flex items-center gap-2 mt-3 text-[#8e8e8e]">
                          <button
                            onClick={() => handleCopyMessage(msg.id, msg.content)}
                            className="p-1.5 hover:text-white hover:bg-[#2f2f2f] rounded-lg transition-colors cursor-pointer"
                            title="Copy response"
                          >
                            {copiedMessageId === msg.id ? (
                              <Check className="w-4 h-4 text-emerald-400" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            className="p-1.5 hover:text-white hover:bg-[#2f2f2f] rounded-lg transition-colors cursor-pointer"
                            title="Good response"
                          >
                            <ThumbsUp className="w-4 h-4" />
                          </button>
                          <button
                            className="p-1.5 hover:text-white hover:bg-[#2f2f2f] rounded-lg transition-colors cursor-pointer"
                            title="Bad response"
                          >
                            <ThumbsDown className="w-4 h-4" />
                          </button>
                          {msg.diagnostics?.total_latency_ms && (
                            <button
                              onClick={() =>
                                setExpandedDiagnostics((prev) => ({
                                  ...prev,
                                  [msg.id]: !prev[msg.id],
                                }))
                              }
                              className="text-[11px] font-mono px-2 py-1 rounded hover:bg-[#2f2f2f] transition-colors flex items-center gap-1"
                            >
                              <span>Diagnostics</span>
                              {isDiagExpanded ? (
                                <ChevronUp className="w-3 h-3" />
                              ) : (
                                <ChevronDown className="w-3 h-3" />
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Live Streaming Message Card */}
            {isStreaming && (
              <div className="w-full space-y-3">
                <div className="flex items-center gap-2.5 text-xs text-[#8e8e8e]">
                  <div className="w-7 h-7 rounded-full bg-[#343541] border border-indigo-500/50 flex items-center justify-center text-rose-400 font-bold text-xs animate-pulse">
                    <Sparkles className="w-4 h-4 text-rose-400" />
                  </div>
                  <span className="font-medium text-white text-sm">Ruby</span>
                  <span className="text-rose-400 animate-pulse font-mono">• Formulating response</span>
                  {streamingSources.length > 0 && (
                    <span className="text-[11px] font-mono text-[#a1a1aa]">
                      ({streamingSources.length} source chunks loaded)
                    </span>
                  )}
                </div>

                <div className="pl-9 text-[15px] leading-7 text-[#ececec]">
                  {streamingText ? (
                    <MarkdownRenderer content={streamingText} />
                  ) : (
                    <div className="text-sm text-[#8e8e8e] animate-pulse">
                      Retrieving evidence & formulating academic answer...
                    </div>
                  )}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        ) : (
          /* ChatGPT Empty State ("New Chat" Screen) */
          <div className="h-full flex flex-col items-center justify-center px-4 max-w-2xl mx-auto text-center space-y-7 -mt-10">
            {/* Greeting Icon & Heading */}
            <div className="space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-rose-600/10 border border-rose-500/20 flex items-center justify-center mx-auto text-rose-400 shadow-lg">
                <Sparkles className="w-7 h-7" />
              </div>
              <h2 className="text-3xl font-medium tracking-tight text-[#ececec]">
                What can I help you learn today?
              </h2>
              <p className="text-sm text-[#8e8e8e] max-w-md mx-auto leading-relaxed">
                Local-first academic copilot grounded in your course materials, lecture slides, and notes with zero cloud leakage.
              </p>
            </div>

            {/* Prompt Suggestion Cards (2x2 Grid) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
              {PROMPT_SUGGESTIONS.map((item, idx) => {
                const Icon = item.icon;
                return (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(item.prompt)}
                    className="p-4 rounded-2xl border border-[#333333] bg-[#282828]/70 hover:bg-[#2f2f2f] transition-all group flex flex-col justify-between cursor-pointer shadow-sm text-left"
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <Icon className="w-4 h-4 text-rose-400 group-hover:scale-110 transition-transform" />
                      <span className="font-medium text-sm text-[#ececec]">{item.title}</span>
                    </div>
                    <p className="text-xs text-[#8e8e8e] leading-relaxed line-clamp-2">
                      {item.prompt}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Floating Bottom Input Pill (ChatGPT Style) */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#212121] via-[#212121]/95 to-transparent pt-6 pb-4 px-4 z-20">
        <div className="max-w-3xl mx-auto w-full">
          {/* Capsule Container */}
          <div className="rounded-[28px] bg-[#2f2f2f] border border-[#383838] focus-within:border-[#555] shadow-2xl p-2 flex flex-col transition-all">
            {/* Textarea */}
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder={`Ask anything about your courses or notes in ${chatMode} mode...`}
              className="w-full bg-transparent text-[#ececec] placeholder:text-[#8e8e8e] text-[15px] px-3 pt-1.5 pb-1 resize-none outline-none max-h-52 overflow-y-auto leading-relaxed"
            />

            {/* Inner Bottom Controls Toolbar */}
            <div className="flex items-center justify-between px-2 pt-1">
              {/* Left: Mode / Subject Attachments */}
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setSubjectPickerOpen(true)}
                  className="p-1.5 rounded-full hover:bg-[#3d3d3d] text-[#b4b4b4] hover:text-white transition-colors cursor-pointer"
                  title="Filter course context"
                >
                  <Plus className="w-4 h-4" />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    const modes = ['resource-grounded', 'general', 'hybrid', 'research'];
                    const nextMode = modes[(modes.indexOf(chatMode) + 1) % modes.length];
                    setChatMode(nextMode);
                  }}
                  className="px-2.5 py-1 rounded-full bg-[#242424] hover:bg-[#383838] text-[11px] font-medium text-[#b4b4b4] hover:text-white border border-[#383838] transition-colors flex items-center gap-1 cursor-pointer"
                >
                  {chatMode === 'resource-grounded' && (
                    <Shield className="w-3 h-3 text-emerald-400" />
                  )}
                  {chatMode === 'general' && <Globe className="w-3 h-3 text-blue-400" />}
                  {chatMode === 'hybrid' && <Shuffle className="w-3 h-3 text-purple-400" />}
                  {chatMode === 'research' && <Microscope className="w-3 h-3 text-amber-400" />}
                  <span className="capitalize">{chatMode.replace('-', ' ')}</span>
                </button>
              </div>

              {/* Right: Circular Send / Stop Button */}
              <div>
                {isStreaming ? (
                  <button
                    type="button"
                    onClick={handleStopStream}
                    className="w-8 h-8 rounded-full bg-white text-black hover:bg-neutral-200 flex items-center justify-center cursor-pointer shadow-md transition-transform active:scale-95"
                    title="Stop generating"
                  >
                    <Square className="w-3.5 h-3.5 fill-current" />
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={!inputText.trim()}
                    onClick={() => handleSendMessage()}
                    className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                      inputText.trim()
                        ? 'bg-white text-black hover:bg-neutral-200 cursor-pointer shadow-md active:scale-95'
                        : 'bg-[#424242] text-[#8e8e8e] cursor-not-allowed opacity-50'
                    }`}
                    title="Send prompt (Enter)"
                  >
                    <ArrowUp className="w-4 h-4 stroke-[2.5]" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Footer Disclaimer */}
          <div className="text-center text-[11px] text-[#71717a] mt-2 select-none">
            Ruby can make mistakes. Verify important academic citations against course texts.
          </div>
        </div>
      </div>

      {/* Citation Inspector Modal */}
      {selectedCitationChunk && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#242424] border border-[#383838] rounded-2xl max-w-lg w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#333] pb-3">
              <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-emerald-400" />
                Source Citation Provenance
              </h3>
              <button
                onClick={() => setSelectedCitationChunk(null)}
                className="p-1 rounded-lg text-[#8e8e8e] hover:text-white hover:bg-[#333]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-[#1a1a1a] border border-[#333] space-y-1.5 font-mono text-[#a1a1aa]">
                <div>
                  Document:{' '}
                  <strong className="text-white font-sans">
                    {selectedCitationChunk.document_title}
                  </strong>
                </div>
                {selectedCitationChunk.page_number && (
                  <div>
                    Page Number:{' '}
                    <strong className="text-white">{selectedCitationChunk.page_number}</strong>
                  </div>
                )}
                {selectedCitationChunk.slide_number && (
                  <div>
                    Slide Number:{' '}
                    <strong className="text-white">{selectedCitationChunk.slide_number}</strong>
                  </div>
                )}
                {selectedCitationChunk.sheet_name && (
                  <div>
                    Spreadsheet:{' '}
                    <strong className="text-white">
                      {selectedCitationChunk.sheet_name} ({selectedCitationChunk.cell_range})
                    </strong>
                  </div>
                )}
                {selectedCitationChunk.section_heading && (
                  <div>
                    Section Heading:{' '}
                    <strong className="text-white font-sans">
                      {selectedCitationChunk.section_heading}
                    </strong>
                  </div>
                )}
                <div>
                  Verification Status:{' '}
                  <strong
                    className={
                      selectedCitationChunk.is_verified ? 'text-emerald-400' : 'text-rose-400'
                    }
                  >
                    {selectedCitationChunk.is_verified
                      ? 'Verified in Source Chunks'
                      : 'Unverified Citation'}
                  </strong>
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] text-[#8e8e8e] font-mono">Raw Citation Tag:</span>
                <p className="font-mono text-xs text-[#93c5fd] bg-[#1a1a1a] p-2.5 rounded-xl border border-[#333]">
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
