import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams, useOutletContext } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles,
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
  GraduationCap,
  Calculator,
  Compass,
  Info,
  RefreshCw,
  AlertCircle,
  Brain,
  Loader2,
  Terminal,
  Activity,
  ArrowDown,
} from 'lucide-react';
import {
  fetchConversation,
  createConversation,
  exportConversationMarkdown,
  streamChat,
  ChatMessageItem,
  fetchAgyUsage,
} from '../services/api';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { LayoutContextType } from '../components/layout/AppLayout';
import { ChatHeader, ChatModeDefinition } from '../components/chat/ChatHeader';
import { MessageComposer } from '../components/chat/MessageComposer';
import { ExecutionTimeline, TimelineStep } from '../components/chat/ExecutionTimeline';
import { WebSourceGrid } from '../components/chat/WebSourceCard';

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

const CHAT_MODES: ChatModeDefinition[] = [
  {
    id: 'auto',
    name: 'Auto',
    icon: Sparkles,
    color: 'text-indigo-400',
    borderColor: 'border-indigo-500/40',
    summary: 'Automatically selects the most appropriate chat mode and tools based on your request.',
    whenToUse: 'Recommended default: let Ruby automatically determine whether you need course notes, web search, math solvers, or code sandboxes.',
  },
  {
    id: 'resource-grounded',
    name: 'Grounded',
    icon: Shield,
    color: 'text-emerald-400',
    borderColor: 'border-emerald-500/40',
    summary: 'Answers strictly from your uploaded course notes & textbooks with exact page citations.',
    whenToUse: 'Use when studying exam notes, preparing for tests, or verifying course material.',
  },
  {
    id: 'web-search',
    name: 'Web Search',
    icon: Globe,
    color: 'text-sky-400',
    borderColor: 'border-sky-500/40',
    summary: 'Searches the live web exclusively via SearXNG without querying local course documents.',
    whenToUse: 'Use for current events, online documentation, latest library updates, and real-time external info.',
  },
  {
    id: 'coding',
    name: 'Coding',
    icon: Terminal,
    color: 'text-teal-400',
    borderColor: 'border-teal-500/40',
    summary: 'Executes Python code in sandboxes, traces algorithms (DSA), and verifies syntax.',
    whenToUse: 'Use when developing software, dry-running algorithms, or analyzing time and space complexities.',
  },
  {
    id: 'general',
    name: 'General',
    icon: Compass,
    color: 'text-blue-400',
    borderColor: 'border-blue-500/40',
    summary: 'Answers using broad academic AI knowledge without consulting your uploaded documents.',
    whenToUse: 'Use for open-ended brainstorming, asking general questions, or when you have not uploaded notes.',
  },
  {
    id: 'hybrid',
    name: 'Hybrid',
    icon: Shuffle,
    color: 'text-purple-400',
    borderColor: 'border-purple-500/40',
    summary: 'Combines your uploaded document evidence with supplementary academic insights.',
    whenToUse: 'Use when you want your syllabus coverage plus broader background context to deepen understanding.',
  },
  {
    id: 'research',
    name: 'Research',
    icon: Microscope,
    color: 'text-amber-400',
    borderColor: 'border-amber-500/40',
    summary: 'Deep cross-document comparison and synthesis across multiple uploaded books or papers.',
    whenToUse: 'Use for literature reviews, comparing different authors, or contrasting textbook definitions.',
  },
];

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
  const outletCtx = useOutletContext<LayoutContextType>();
  const isSidebarOpen = outletCtx?.isSidebarOpen ?? true;
  const onToggleSidebar = outletCtx?.onToggleSidebar;

  const activeConvId = searchParams.get('c');

  // Chat Configuration State
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [chatMode, setChatMode] = useState<string>('auto');
  const [inputText, setInputText] = useState('');
  const [webSearchEnabled, setWebSearchEnabled] = useState<boolean>(false);
  const [autoModeRouted, setAutoModeRouted] = useState<{ effective_mode: string; explanation: string } | null>(null);
  const [agyUsageOpen, setAgyUsageOpen] = useState(false);

  // Streaming State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingSources, setStreamingSources] = useState<any[]>([]);
  const [streamingWebSources, setStreamingWebSources] = useState<any[]>([]);
  const [streamingMemories, setStreamingMemories] = useState<any[]>([]);
  const [streamingMemorySaved, setStreamingMemorySaved] = useState<any | null>(null);
  const [streamingSteps, setStreamingSteps] = useState<TimelineStep[]>([]);
  const [streamingThinking, setStreamingThinking] = useState<string>('');
  const [isSearchingWeb, setIsSearchingWeb] = useState(false);
  const [webSearchQuery, setWebSearchQuery] = useState('');
  const [abortStream, setAbortStream] = useState<(() => void) | null>(null);

  // Optimistic & Error State
  const [optimisticUserMsg, setOptimisticUserMsg] = useState<ChatMessageItem | null>(null);
  const [chatError, setChatError] = useState<{ message: string; retryPrompt: string } | null>(null);

  // Modals & Panels
  const [selectedCitationChunk, setSelectedCitationChunk] = useState<any | null>(null);
  const [expandedDiagnostics, setExpandedDiagnostics] = useState<Record<string, boolean>>({});
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [subjectPickerOpen, setSubjectPickerOpen] = useState(false);
  const [modeHelpOpen, setModeHelpOpen] = useState(false);
  const [helpGuideOpen, setHelpGuideOpen] = useState(false);

  // Scrolling state
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = useState(false);

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

  const { data: agyUsage, refetch: refetchAgyUsage, isFetching: isAgyUsageLoading } = useQuery({
    queryKey: ['agyUsage'],
    queryFn: fetchAgyUsage,
    enabled: agyUsageOpen,
  });

  const activeProvider = providers?.find((p: any) => p.is_default) || providers?.[0];

  // Unified message list reconciling optimistic user prompt with database
  const displayMessages = useMemo(() => {
    const list = [...(currentConv?.messages || [])];
    if (optimisticUserMsg) {
      const alreadyInList = list.some(
        (m) => m.role === 'user' && m.content === optimisticUserMsg.content
      );
      if (!alreadyInList) {
        list.push(optimisticUserMsg);
      }
    }
    return list;
  }, [currentConv?.messages, optimisticUserMsg]);

  // Handle user scroll detection
  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    // If user is more than 120px away from the bottom, mark as scrolled up
    setUserScrolledUp(distanceFromBottom > 120);
  };

  const scrollToBottom = (smooth = true) => {
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
    setUserScrolledUp(false);
  };

  // Predictable auto-scrolling: only auto-scroll if user has NOT scrolled up
  useEffect(() => {
    if (!userScrolledUp) {
      scrollToBottom(false);
    }
  }, [displayMessages, streamingText, chatError]);

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

    const optUser: ChatMessageItem = {
      id: `opt-${Date.now()}`,
      conversation_id: targetConvId,
      role: 'user',
      content: textToSend,
      mode: chatMode,
      created_at: new Date().toISOString(),
    };

    setOptimisticUserMsg(optUser);
    setChatError(null);
    setInputText('');
    setUserScrolledUp(false);

    setIsStreaming(true);
    setStreamingText('');
    setStreamingSources([]);
    setStreamingWebSources([]);
    setStreamingMemories([]);
    setStreamingMemorySaved(null);
    setStreamingSteps([]);
    setStreamingThinking('');
    setIsSearchingWeb(false);
    setWebSearchQuery('');
    setAutoModeRouted(null);

    const cancel = streamChat(
      {
        conversation_id: targetConvId,
        content: textToSend,
        mode: chatMode,
        subject_id: selectedSubjectId || undefined,
        web_search: webSearchEnabled || chatMode === 'web-search',
      },
      {
        onSources: (chunks) => {
          setStreamingSources(chunks);
        },
        onWebSearchStart: (q) => {
          setIsSearchingWeb(true);
          setWebSearchQuery(q);
        },
        onWebSources: (sources) => {
          setIsSearchingWeb(false);
          setStreamingWebSources(sources);
        },
        onWebSearchError: () => {
          setIsSearchingWeb(false);
        },
        onAutoModeRouted: (data) => {
          setAutoModeRouted(data);
        },
        onMemories: (mems) => {
          setStreamingMemories(mems);
        },
        onMemorySaved: (mem) => {
          setStreamingMemorySaved(mem);
        },
        onStep: (step) => {
          setStreamingSteps((prev) => {
            const idx = prev.findIndex((s) => s.id === step.id);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = step;
              return next;
            }
            return [...prev, step];
          });
        },
        onThinkToken: (thinkToken) => {
          setStreamingThinking((prev) => prev + thinkToken);
        },
        onToken: (token) => {
          setStreamingText((prev) => prev + token);
        },
        onDone: () => {
          setIsStreaming(false);
          setStreamingText('');
          setStreamingSources([]);
          setStreamingWebSources([]);
          setStreamingMemories([]);
          setStreamingMemorySaved(null);
          setStreamingSteps([]);
          setStreamingThinking('');
          setIsSearchingWeb(false);
          setOptimisticUserMsg(null);
          refetchCurrentConv();
          queryClient.invalidateQueries({ queryKey: ['conversations'] });
        },
        onError: (err) => {
          setIsStreaming(false);
          setIsSearchingWeb(false);
          setChatError({
            message: err || 'An unexpected error occurred during chat generation.',
            retryPrompt: textToSend,
          });
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
    setIsSearchingWeb(false);
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
  const hasMessages = displayMessages.length > 0 || isStreaming || !!chatError;

  return (
    <div className="flex-1 flex flex-col h-full bg-[#212121] text-[#ececec] relative overflow-hidden select-text">
      {/* Reorganized Premium Chat Header */}
      <ChatHeader
        activeProvider={activeProvider}
        providers={providers}
        selectedSubjectId={selectedSubjectId}
        subjects={subjects}
        onSelectSubject={(id) => setSelectedSubjectId(id)}
        chatMode={chatMode}
        chatModes={CHAT_MODES}
        onSelectChatMode={(id) => setChatMode(id)}
        onOpenModeHelp={() => setModeHelpOpen(true)}
        onOpenSystemGuide={() => setHelpGuideOpen(true)}
        onOpenAgyUsage={() => setAgyUsageOpen(true)}
        onExportMarkdown={handleExportMarkdown}
        canExport={!!currentConv}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={onToggleSidebar}
      />

      {/* Main Conversation Stream */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto relative"
      >
        {hasMessages ? (
          <div className="max-w-4xl mx-auto w-full px-4 sm:px-6 pt-6 pb-48 space-y-7">
            {displayMessages.map((msg: ChatMessageItem) => {
              const isUser = msg.role === 'user';
              const isDiagExpanded = !!expandedDiagnostics[msg.id];
              const webSources = msg.diagnostics?.web_sources || [];
              const steps = msg.diagnostics?.steps || [];
              const thinkingContent = msg.diagnostics?.thinking_content || '';

              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  {isUser ? (
                    /* User Message Bubble - Elevated card with crisp border */
                    <div className="user-msg-bubble">
                      <p className="whitespace-pre-wrap break-words text-[15px]">{msg.content}</p>
                    </div>
                  ) : (
                    /* Assistant Message - Full-width clean container with Ruby avatar */
                    <div className="assistant-msg-container space-y-3">
                      {/* Avatar & Header */}
                      <div className="flex items-center gap-2 text-xs text-[#8e8e8e]">
                        <div className="w-6 h-6 rounded-lg bg-rose-600/15 border border-rose-500/30 flex items-center justify-center text-rose-400 font-bold shadow-sm">
                          <Sparkles className="w-3.5 h-3.5 text-rose-400" />
                        </div>
                        <span className="font-semibold text-white text-sm">Ruby</span>
                        <span>•</span>
                        <span className="capitalize text-[#a1a1aa]">
                          {(msg.mode || 'Grounded').replace('-', ' ')}
                        </span>
                        {msg.diagnostics?.requested_mode === 'auto' && (
                          <span
                            className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-950/80 text-indigo-300 border border-indigo-700/50"
                            title={msg.diagnostics.mode_explanation || 'Auto routed by Ruby Agent'}
                          >
                            Auto
                          </span>
                        )}
                        {msg.diagnostics?.total_latency_ms && (
                          <>
                            <span>•</span>
                            <span className="font-mono text-[11px] text-[#71717a]">
                              {msg.diagnostics.total_latency_ms}ms
                            </span>
                          </>
                        )}
                      </div>

                      {/* Content Area */}
                      <div className="pl-8 text-[15px] leading-relaxed text-[#ececec]">
                        {/* Modular Collapsible Execution Timeline */}
                        <ExecutionTimeline
                          steps={steps}
                          thinkingContent={thinkingContent}
                          totalDurationMs={msg.diagnostics?.total_latency_ms}
                          recalledMemoriesCount={msg.diagnostics?.recalled_memories_count}
                          newMemoriesCount={msg.diagnostics?.newly_formed_memories_count}
                          autoModeExplanation={
                            msg.diagnostics?.requested_mode === 'auto'
                              ? msg.diagnostics?.mode_explanation
                              : undefined
                          }
                        />

                        {/* Main Response Markdown */}
                        <MarkdownRenderer
                          content={msg.content}
                          onCitationClick={(tag) => {
                            const matched = msg.citations?.find((c: any) => c.raw_tag === tag);
                            if (matched) {
                              setSelectedCitationChunk(matched);
                            }
                          }}
                        />

                        {/* Verified Local Course Document Citations */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-4 pt-3 border-t border-[#2e2e2e] space-y-2">
                            <span className="text-xs font-medium text-[#8e8e8e] flex items-center gap-1.5">
                              <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
                              Course Document Sources ({msg.citations.length}):
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {msg.citations.map((c: any, cIdx: number) => (
                                <button
                                  key={cIdx}
                                  onClick={() => setSelectedCitationChunk(c)}
                                  className={`flex items-center gap-1.5 text-xs font-mono px-3 py-1 rounded-lg border transition-colors cursor-pointer shadow-sm ${
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

                        {/* Perplexity/Claude-Style Web Sources Card Grid */}
                        {webSources.length > 0 && <WebSourceGrid sources={webSources} />}

                        {/* Diagnostics Detail Box (Collapsible) */}
                        {isDiagExpanded && msg.diagnostics && (
                          <div className="mt-3 p-3 bg-[#191919] rounded-xl border border-[#333] text-xs font-mono text-[#a1a1aa] space-y-1">
                            <div>Retrieval Latency: {msg.diagnostics.retrieval_latency_ms} ms</div>
                            <div>Generation Latency: {msg.diagnostics.generation_latency_ms} ms</div>
                            <div>Total Latency: {msg.diagnostics.total_latency_ms} ms</div>
                            <div>Tokens Used: ~{msg.tokens_used}</div>
                            {msg.diagnostics.web_sources_count !== undefined && (
                              <div>Live Web Sources: {msg.diagnostics.web_sources_count}</div>
                            )}
                            {msg.diagnostics.recalled_memories_count !== undefined && (
                              <div className="text-purple-300">
                                Recalled Long-Term Memories: {msg.diagnostics.recalled_memories_count}
                              </div>
                            )}
                            {msg.diagnostics.newly_formed_memories_count !== undefined && msg.diagnostics.newly_formed_memories_count > 0 && (
                              <div className="text-purple-400 font-semibold">
                                Stored New Memories: {msg.diagnostics.newly_formed_memories_count}
                              </div>
                            )}
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

                        {/* Bottom Action Bar */}
                        <div className="flex items-center gap-2 mt-3 text-[#8e8e8e]">
                          <button
                            onClick={() => handleCopyMessage(msg.id, msg.content)}
                            className="p-1.5 hover:text-white hover:bg-[#2a2a2a] rounded-lg transition-colors cursor-pointer"
                            title="Copy response"
                          >
                            {copiedMessageId === msg.id ? (
                              <Check className="w-4 h-4 text-emerald-400" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            className="p-1.5 hover:text-white hover:bg-[#2a2a2a] rounded-lg transition-colors cursor-pointer"
                            title="Good response"
                          >
                            <ThumbsUp className="w-4 h-4" />
                          </button>
                          <button
                            className="p-1.5 hover:text-white hover:bg-[#2a2a2a] rounded-lg transition-colors cursor-pointer"
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
                              className="text-[11px] font-mono px-2 py-1 rounded hover:bg-[#2a2a2a] text-[#8e8e8e] hover:text-[#ececec] transition-colors flex items-center gap-1 cursor-pointer"
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
                <div className="flex items-center gap-2 text-xs text-[#8e8e8e]">
                  <div className="w-6 h-6 rounded-lg bg-rose-600/20 border border-rose-500/50 flex items-center justify-center text-rose-400 font-bold shadow-sm animate-pulse">
                    <Sparkles className="w-3.5 h-3.5 text-rose-400" />
                  </div>
                  <span className="font-semibold text-white text-sm">Ruby</span>
                  <span className="text-rose-400 animate-pulse font-mono">• Generating response</span>
                  {streamingSources.length > 0 && (
                    <span className="text-[11px] font-mono text-[#a1a1aa]">
                      ({streamingSources.length} chunks)
                    </span>
                  )}
                  {streamingWebSources.length > 0 && (
                    <span className="text-[11px] font-mono text-sky-400">
                      ({streamingWebSources.length} web sources)
                    </span>
                  )}
                  {streamingMemories.length > 0 && (
                    <span className="text-[11px] font-mono text-purple-400">
                      ({streamingMemories.length} memories)
                    </span>
                  )}
                </div>

                <div className="pl-8 space-y-3">
                  {/* Live Execution Timeline */}
                  <ExecutionTimeline
                    steps={streamingSteps}
                    thinkingContent={streamingThinking}
                    isLive={true}
                    autoModeExplanation={autoModeRouted?.explanation}
                    defaultExpanded={true}
                  />

                  {/* Live Web Search Querying Banner */}
                  {isSearchingWeb && (
                    <div className="flex items-center gap-2 text-xs text-sky-400 bg-sky-950/40 border border-sky-800/60 p-2.5 rounded-xl animate-pulse">
                      <Globe className="w-4 h-4 animate-spin shrink-0 text-sky-400" />
                      <span>Querying SearXNG live web index for: &quot;{webSearchQuery}&quot;...</span>
                    </div>
                  )}

                  {/* Live Memory Saved Banner */}
                  {streamingMemorySaved && (
                    <div className="flex items-center gap-2 text-xs text-purple-300 bg-purple-950/40 border border-purple-800/60 p-2.5 rounded-xl">
                      <Brain className="w-4 h-4 shrink-0 text-purple-400" />
                      <span>Stored in Long-Term Memory: <strong>{streamingMemorySaved.content}</strong></span>
                    </div>
                  )}

                  {/* Live Streaming Web Sources Grid */}
                  {streamingWebSources.length > 0 && (
                    <WebSourceGrid sources={streamingWebSources} defaultExpanded={true} />
                  )}

                  {/* Main Streaming Output */}
                  <div className="text-[15px] leading-relaxed text-[#ececec]">
                    {streamingText ? (
                      <MarkdownRenderer content={streamingText} />
                    ) : (
                      <div className="text-sm text-[#8e8e8e] animate-pulse flex items-center gap-2 py-2">
                        <Loader2 className="w-4 h-4 text-rose-400 animate-spin" />
                        <span>Formulating academic response...</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Chat Error Card with Retry Button */}
            {chatError && (
              <div className="w-full pl-8">
                <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-800/60 text-xs text-rose-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
                  <div className="flex items-start gap-2.5">
                    <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold text-sm text-white">Generation Error</div>
                      <p className="mt-0.5 text-rose-300 leading-relaxed">{chatError.message}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleSendMessage(chatError.retryPrompt)}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-medium transition-colors cursor-pointer shadow shrink-0"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Retry Request</span>
                  </button>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        ) : (
          /* Empty State ("New Chat" Screen) */
          <div className="h-full flex flex-col items-center justify-center px-4 max-w-2xl mx-auto text-center space-y-7 -mt-10">
            <div className="space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-rose-600/10 border border-rose-500/20 flex items-center justify-center mx-auto text-rose-400 shadow-lg">
                <Sparkles className="w-7 h-7" />
              </div>
              <h2 className="text-3xl font-medium tracking-tight text-[#ececec]">
                What can I help you learn today?
              </h2>
              <p className="text-sm text-[#8e8e8e] max-w-md mx-auto leading-relaxed">
                Local-first academic copilot grounded in your course materials with zero cloud leakage, SearXNG web search, and step-by-step reasoning.
              </p>
            </div>

            {/* 2x2 Prompt Suggestions Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
              {PROMPT_SUGGESTIONS.map((item, idx) => {
                const Icon = item.icon;
                return (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(item.prompt)}
                    className="p-4 rounded-xl border border-[#333333] bg-[#262626] hover:bg-[#2d2d2d] hover:border-[#4d4d4d] transition-all group flex flex-col justify-between cursor-pointer shadow-sm text-left"
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

        {/* Floating "Scroll to bottom" button when user scrolled up */}
        {userScrolledUp && hasMessages && (
          <button
            onClick={() => scrollToBottom(true)}
            className="fixed bottom-28 right-6 z-30 p-2.5 rounded-full bg-[#2c2c2c] hover:bg-[#383838] border border-[#444444] text-[#ececec] shadow-xl transition-all cursor-pointer flex items-center gap-1.5 text-xs font-medium"
            title="Scroll to bottom"
          >
            <ArrowDown className="w-4 h-4" />
            <span className="hidden sm:inline">Latest</span>
          </button>
        )}
      </div>

      {/* Floating Bottom Composer */}
      <MessageComposer
        inputText={inputText}
        onChangeText={setInputText}
        onSendMessage={handleSendMessage}
        isStreaming={isStreaming}
        onStopStream={handleStopStream}
        chatMode={chatMode}
        chatModes={CHAT_MODES}
        onChangeChatMode={setChatMode}
        webSearchEnabled={webSearchEnabled}
        onToggleWebSearch={() => setWebSearchEnabled((prev) => !prev)}
        onOpenSubjectPicker={() => setSubjectPickerOpen(true)}
        selectedSubjectName={selectedSubject?.name}
      />

      {/* Subject Context Picker Modal */}
      {subjectPickerOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#242424] border border-[#383838] rounded-2xl max-w-sm w-full p-4 shadow-2xl space-y-3">
            <div className="flex items-center justify-between border-b border-[#333] pb-2.5">
              <h3 className="font-semibold text-white text-sm">Select Course Context</h3>
              <button
                onClick={() => setSubjectPickerOpen(false)}
                className="p-1 rounded-lg text-[#8e8e8e] hover:text-white hover:bg-[#333]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-1 max-h-60 overflow-y-auto">
              <button
                onClick={() => {
                  setSelectedSubjectId('');
                  setSubjectPickerOpen(false);
                }}
                className={`w-full text-left p-2 rounded-lg text-xs transition-colors ${
                  !selectedSubjectId
                    ? 'bg-[#333333] text-white font-medium'
                    : 'text-[#b4b4b4] hover:bg-[#2c2c2c]'
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
                  className={`w-full text-left p-2 rounded-lg text-xs truncate transition-colors ${
                    selectedSubjectId === s.id
                      ? 'bg-[#333333] text-white font-medium'
                      : 'text-[#b4b4b4] hover:bg-[#2c2c2c]'
                  }`}
                >
                  {s.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Mode Discoverability Help Modal */}
      {modeHelpOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#242424] border border-[#383838] rounded-2xl max-w-lg w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#333] pb-3">
              <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                <Info className="w-4 h-4 text-rose-400" />
                Understanding Ruby Chat Modes
              </h3>
              <button
                onClick={() => setModeHelpOpen(false)}
                className="p-1 rounded-lg text-[#8e8e8e] hover:text-white hover:bg-[#333]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2.5 max-h-[70vh] overflow-y-auto pr-1">
              {CHAT_MODES.map((m) => {
                const Icon = m.icon;
                return (
                  <div
                    key={m.id}
                    onClick={() => {
                      setChatMode(m.id);
                      setModeHelpOpen(false);
                    }}
                    className={`p-3.5 rounded-xl border ${m.borderColor} bg-[#1a1a1a] hover:bg-[#262626] cursor-pointer transition-all space-y-1`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className={`w-4 h-4 ${m.color}`} />
                        <span className="font-semibold text-sm text-white">{m.name} Mode</span>
                      </div>
                      {chatMode === m.id && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/70 text-emerald-400 border border-emerald-800">
                          Active
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#ececec]">{m.summary}</p>
                    <p className="text-[11px] text-[#8e8e8e] italic">Best when: {m.whenToUse}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Comprehensive System & Features Getting Started Guide Modal */}
      {helpGuideOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#242424] border border-[#383838] rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-[#333] pb-3 sticky top-0 bg-[#242424] z-10">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-rose-600/20 border border-rose-500/30 flex items-center justify-center text-rose-400 font-bold text-sm">
                  R
                </div>
                <div>
                  <h3 className="font-semibold text-white text-base">Ruby Academic Copilot Guide</h3>
                  <p className="text-[11px] text-[#8e8e8e]">Architecture, features, and tools handbook</p>
                </div>
              </div>
              <button
                onClick={() => setHelpGuideOpen(false)}
                className="p-1 rounded-lg text-[#8e8e8e] hover:text-white hover:bg-[#333]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs text-[#d1d5db] leading-relaxed">
              <div className="p-3.5 rounded-xl bg-[#1a1a1a] border border-[#333] space-y-1">
                <h4 className="font-semibold text-white text-sm">What is Ruby?</h4>
                <p>
                  Ruby is a personal, local-first academic intelligence copilot. It runs on your own machine without sending your private research, notes, or credentials to third-party clouds unless you explicitly configure an external provider.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#1a1a1a] border border-[#333] space-y-2">
                <h4 className="font-semibold text-white text-sm">Document-Based Retrieval (RAG)</h4>
                <p>
                  Upload your textbooks, PDFs, PPTX lecture slides, DOCX notes, or spreadsheets in the <strong>Library</strong>. Ruby chunks, embeds, and indexes them using a local vector store and BM25 full-text search.
                </p>
                <p>
                  In <strong>Grounded Mode</strong>, answers quote verbatim sources and supply clickable citations with exact page numbers.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#1a1a1a] border border-[#333] space-y-2">
                <h4 className="font-semibold text-white text-sm">SearXNG Live Web Search & Web Search Mode</h4>
                <p>
                  Switch to <strong>Web Search Mode</strong> to search the internet exclusively via SearXNG without querying local course documents. Or use the <strong>Web Search</strong> toggle button in any other mode to enrich answers with live web intelligence.
                </p>
                <p>
                  Web results are cited with rich source cards and direct references.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#1a1a1a] border border-[#333] space-y-2">
                <h4 className="font-semibold text-white text-sm">Execution Activity Trace & AI Thinking</h4>
                <p>
                  Watch real-time operational steps unfold as Ruby analyzes your query, searches course documents, executes SearXNG web queries, and validates citations. For reasoning models, the internal chain of thought streams live in a collapsible thought process box.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#1a1a1a] border border-[#333] space-y-2">
                <h4 className="font-semibold text-white text-sm">Academic Simulators & Math Engine</h4>
                <ul className="list-disc list-inside space-y-1 text-[#b4b4b4]">
                  <li><strong>SymPy Math Engine:</strong> Solves algebraic equations, derivatives, integrals, and matrix operations.</li>
                  <li><strong>Restricted Code Sandbox:</strong> Executes Python and traces algorithm steps safely with AST reflection blocking.</li>
                  <li><strong>OS & Network Simulators:</strong> Simulates CPU scheduling, Banker&apos;s deadlock avoidance, FIFO/LRU page replacement, IPv4 subnets, and logic gates.</li>
                  <li><strong>FSRS Spaced Repetition:</strong> Generates and schedules memory flashcards using the Free Spaced Repetition Schedule (FSRS v4).</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

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

      {/* AGY Quotas & Usage Dashboard Modal */}
      {agyUsageOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#242424] border border-[#383838] rounded-2xl w-full max-w-xl shadow-2xl p-6 text-[#ececec]">
            <div className="flex items-center justify-between pb-4 border-b border-[#333]">
              <div className="flex items-center gap-2.5">
                <Activity className="w-5 h-5 text-indigo-400" />
                <h2 className="text-base font-semibold text-white">AGY CLI Quotas & Usage Dashboard</h2>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => refetchAgyUsage()}
                  disabled={isAgyUsageLoading}
                  className="p-1.5 rounded-lg hover:bg-[#333] text-[#a1a1aa] hover:text-white transition-colors cursor-pointer"
                  title="Refresh Quotas"
                >
                  <RefreshCw className={`w-4 h-4 ${isAgyUsageLoading ? 'animate-spin text-indigo-400' : ''}`} />
                </button>
                <button
                  onClick={() => setAgyUsageOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-[#333] text-[#a1a1aa] hover:text-white transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="mt-4 space-y-4 max-h-[70vh] overflow-y-auto pr-1">
              {isAgyUsageLoading ? (
                <div className="py-8 flex flex-col items-center justify-center gap-2 text-sm text-[#a1a1aa]">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                  <span>Fetching live quotas from AGY CLI...</span>
                </div>
              ) : agyUsage?.groups && agyUsage.groups.length > 0 ? (
                <>
                  <p className="text-xs text-[#a1a1aa] leading-relaxed">
                    {agyUsage.general_description ||
                      'Within each group, models share a weekly limit and a 5-hour limit. Quota is consumed proportionally.'}
                  </p>
                  {agyUsage.groups.map((group: any, gIdx: number) => (
                    <div key={gIdx} className="p-4 rounded-xl bg-[#1c1c1c] border border-[#333] space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-white">{group.name}</h3>
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-[#2e2e2e] text-indigo-300 border border-[#3e3e3e]">
                          Shared Group
                        </span>
                      </div>
                      {group.description && (
                        <p className="text-xs text-[#8e8e8e]">{group.description}</p>
                      )}
                      <div className="space-y-3 pt-1">
                        {group.buckets?.map((bucket: any, bIdx: number) => (
                          <div key={bIdx} className="space-y-1.5">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-[#ccc] font-medium">{bucket.name}</span>
                              <span className="font-mono text-indigo-300 font-semibold">
                                {bucket.remaining_percentage}% left ({bucket.used_percentage}% used)
                              </span>
                            </div>
                            <div className="w-full h-2 bg-[#2d2d2d] rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all duration-500 ${
                                  bucket.remaining_percentage > 40
                                    ? 'bg-emerald-500'
                                    : bucket.remaining_percentage > 15
                                    ? 'bg-amber-500'
                                    : 'bg-rose-500'
                                }`}
                                style={{ width: `${bucket.remaining_percentage}%` }}
                              />
                            </div>
                            <div className="flex items-center justify-between text-[11px] text-[#777]">
                              <span>Window: {bucket.window}</span>
                              {bucket.reset_time && (
                                <span>
                                  Resets: {new Date(bucket.reset_time).toLocaleDateString()} {new Date(bucket.reset_time).toLocaleTimeString()}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </>
              ) : (
                <div className="py-6 text-center text-sm text-[#888]">
                  {agyUsage?.error ? (
                    <div className="text-rose-400">{agyUsage.error}</div>
                  ) : (
                    'No active AGY quotas found.'
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
