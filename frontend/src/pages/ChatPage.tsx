import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
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
  HelpCircle,
  Info,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  Brain,
  Loader2,
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

const CHAT_MODES = [
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
  const activeConvId = searchParams.get('c');

  // Chat Configuration State
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [chatMode, setChatMode] = useState<string>('resource-grounded');
  const [inputText, setInputText] = useState('');
  const [webSearchEnabled, setWebSearchEnabled] = useState<boolean>(false);

  // Streaming State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingSources, setStreamingSources] = useState<any[]>([]);
  const [streamingWebSources, setStreamingWebSources] = useState<any[]>([]);
  const [streamingMemories, setStreamingMemories] = useState<any[]>([]);
  const [streamingMemorySaved, setStreamingMemorySaved] = useState<any | null>(null);
  const [streamingSteps, setStreamingSteps] = useState<any[]>([]);
  const [streamingThinking, setStreamingThinking] = useState<string>('');
  const [isLiveThinkingExpanded, setIsLiveThinkingExpanded] = useState<boolean>(true);
  const [isSearchingWeb, setIsSearchingWeb] = useState(false);
  const [webSearchQuery, setWebSearchQuery] = useState('');
  const [abortStream, setAbortStream] = useState<(() => void) | null>(null);

  // Optimistic & Error State (Fix for Issue A & B)
  const [optimisticUserMsg, setOptimisticUserMsg] = useState<ChatMessageItem | null>(null);
  const [chatError, setChatError] = useState<{ message: string; retryPrompt: string } | null>(null);

  // Modals & Panels
  const [selectedCitationChunk, setSelectedCitationChunk] = useState<any | null>(null);
  const [expandedDiagnostics, setExpandedDiagnostics] = useState<Record<string, boolean>>({});
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [modelPickerOpen, setModelPickerOpen] = useState(false);
  const [subjectPickerOpen, setSubjectPickerOpen] = useState(false);
  const [modeHelpOpen, setModeHelpOpen] = useState(false);
  const [helpGuideOpen, setHelpGuideOpen] = useState(false);

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

  // Unified message list reconciling optimistic user prompt with database (Issue B Root Cause Fix)
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

  // Scroll to bottom on new messages or streaming
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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

    // Immediately create and show the optimistic user message (Issue B Root Cause Fix)
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
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    setIsStreaming(true);
    setStreamingText('');
    setStreamingSources([]);
    setStreamingWebSources([]);
    setStreamingMemories([]);
    setStreamingMemorySaved(null);
    setStreamingSteps([]);
    setStreamingThinking('');
    setIsLiveThinkingExpanded(true);
    setIsSearchingWeb(false);
    setWebSearchQuery('');

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
          // Meaningful error message with retry option (Issue A Root Cause Fix)
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
  const activeModeObj = CHAT_MODES.find((m) => m.id === chatMode) || CHAT_MODES[0];

  const hasMessages = displayMessages.length > 0 || isStreaming || !!chatError;

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
                      p.is_default ? 'bg-[#383838] text-white' : 'hover:bg-[#333333] text-[#b4b4b4]'
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
                      selectedSubjectId === s.id ? 'bg-[#383838] text-white' : 'text-[#b4b4b4] hover:bg-[#333]'
                    }`}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Mode Switcher Group with Discoverability Tooltip/Help */}
          <div className="flex items-center bg-[#282828] p-0.5 rounded-xl border border-[#383838]">
            {CHAT_MODES.map((mode) => {
              const Icon = mode.icon;
              const isActive = chatMode === mode.id;
              return (
                <button
                  key={mode.id}
                  onClick={() => setChatMode(mode.id)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                    isActive ? 'bg-[#3e3e3e] text-white shadow-sm' : 'text-[#b4b4b4] hover:text-white'
                  }`}
                  title={`${mode.name} Mode: ${mode.summary}`}
                >
                  <Icon className={`w-3.5 h-3.5 ${mode.color}`} />
                  <span className="hidden sm:inline">{mode.name}</span>
                </button>
              );
            })}

            {/* Mode Guide Info Button */}
            <button
              onClick={() => setModeHelpOpen(true)}
              className="p-1 text-[#8e8e8e] hover:text-[#ececec] rounded hover:bg-[#383838] transition-colors ml-0.5"
              title="Explain Chat Modes"
            >
              <Info className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* System Getting Started Guide Button */}
          <button
            onClick={() => setHelpGuideOpen(true)}
            className="p-1.5 text-[#b4b4b4] hover:text-white rounded-lg hover:bg-[#2f2f2f] transition-colors flex items-center gap-1 text-xs"
            title="Ruby System & Features Guide"
          >
            <HelpCircle className="w-4 h-4 text-rose-400" />
            <span className="hidden md:inline text-xs font-medium">Guide</span>
          </button>

          {/* Memory Manager Link */}
          <Link
            to="/memory"
            className="p-1.5 text-[#b4b4b4] hover:text-purple-300 rounded-lg hover:bg-[#2f2f2f] transition-colors flex items-center gap-1 text-xs"
            title="Memory Manager - View and govern persistent long-term memories"
          >
            <Brain className="w-4 h-4 text-purple-400" />
            <span className="hidden lg:inline text-xs font-medium">Memories</span>
          </Link>

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
        {hasMessages ? (
          <div className="max-w-3xl mx-auto w-full px-4 pt-6 pb-44 space-y-7">
            {displayMessages.map((msg: ChatMessageItem) => {
              const isUser = msg.role === 'user';
              const isDiagExpanded = !!expandedDiagnostics[msg.id];
              const webSources = msg.diagnostics?.web_sources || [];

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
                        {/* Claude-Style Thinking & Activity Trace */}
                        {(() => {
                          const steps = msg.diagnostics?.steps || [];
                          const thinkingContent = msg.diagnostics?.thinking_content || '';
                          const hasSteps = steps.length > 0;
                          const hasThinking = !!thinkingContent;
                          if (!hasSteps && !hasThinking) return null;

                          const isExpanded = !!expandedSteps[msg.id];

                          return (
                            <div className="mb-3.5">
                              <button
                                onClick={() =>
                                  setExpandedSteps((prev) => ({
                                    ...prev,
                                    [msg.id]: !prev[msg.id],
                                  }))
                                }
                                className="flex items-center gap-2 text-xs font-medium text-[#b4b4b4] hover:text-white bg-[#262626] hover:bg-[#2e2e2e] px-3 py-1.5 rounded-xl border border-[#383838] transition-all cursor-pointer shadow-sm group"
                              >
                                <Brain className="w-3.5 h-3.5 text-rose-400 group-hover:scale-110 transition-transform" />
                                <span>
                                  {hasThinking ? 'Thought Process & Steps' : 'Execution Activity Trace'}
                                  {steps.length > 0 ? ` (${steps.length} steps)` : ''}
                                </span>
                                {isExpanded ? (
                                  <ChevronUp className="w-3.5 h-3.5 text-[#888]" />
                                ) : (
                                  <ChevronDown className="w-3.5 h-3.5 text-[#888]" />
                                )}
                              </button>

                              {isExpanded && (
                                <div className="mt-2.5 p-3.5 rounded-2xl bg-[#191919] border border-[#333] space-y-3 shadow-inner">
                                  {/* Stepper Timeline */}
                                  {steps.length > 0 && (
                                    <div className="space-y-2.5 text-xs">
                                      {steps.map((st: any) => (
                                        <div key={st.id} className="flex items-start gap-2.5">
                                          {st.status === 'completed' ? (
                                            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                                          ) : st.status === 'failed' ? (
                                            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                                          ) : (
                                            <Loader2 className="w-4 h-4 text-rose-400 animate-spin shrink-0 mt-0.5" />
                                          )}
                                          <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between gap-2">
                                              <span className="font-semibold text-[#f0f0f0]">{st.label}</span>
                                              <span className="text-[10px] font-mono text-[#888] uppercase">{st.status}</span>
                                            </div>
                                            {st.description && (
                                              <p className="text-[#a1a1aa] mt-0.5 leading-relaxed">{st.description}</p>
                                            )}
                                            {st.details && Array.isArray(st.details) && (
                                              <div className="mt-1.5 pl-2.5 border-l-2 border-[#383838] space-y-1">
                                                {st.details.map((d: any, idx: number) => (
                                                  <div key={idx} className="text-[11px] text-[#93c5fd] truncate flex items-center gap-1.5">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0" />
                                                    {typeof d === 'string' ? (
                                                      d
                                                    ) : (
                                                      <a
                                                        href={d.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="hover:underline flex items-center gap-1"
                                                      >
                                                        <span>{d.title}</span>
                                                        <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                                                      </a>
                                                    )}
                                                  </div>
                                                ))}
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  )}

                                  {/* AI Internal Thought Box */}
                                  {hasThinking && (
                                    <div className="pt-2.5 border-t border-[#2d2d2d]">
                                      <div className="text-[11px] font-mono text-rose-300 mb-1.5 flex items-center gap-1.5">
                                        <Sparkles className="w-3.5 h-3.5 text-rose-400" />
                                        <span>Internal Chain of Thought:</span>
                                      </div>
                                      <div className="p-3 rounded-xl bg-[#141414] border border-[#282828] text-xs font-mono text-[#a1a1aa] whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto select-text shadow-inner">
                                        {thinkingContent}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })()}

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

                        {/* Distinct SearXNG Live Web Sources */}
                        {webSources.length > 0 && (
                          <div className="mt-3 pt-2.5 border-t border-[#2e2e2e] space-y-1.5">
                            <span className="text-xs font-medium text-blue-400 flex items-center gap-1.5">
                              <Globe className="w-3.5 h-3.5 text-blue-400" />
                              Live Web Sources via SearXNG ({webSources.length}):
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {webSources.map((w: any, wIdx: number) => (
                                <a
                                  key={wIdx}
                                  href={w.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1.5 text-xs font-mono px-3 py-1 rounded-full border border-blue-800/60 bg-blue-950/40 text-blue-300 hover:bg-blue-900/60 hover:text-white transition-colors cursor-pointer shadow-sm"
                                  title={w.snippet}
                                >
                                  <Globe className="w-3 h-3 text-blue-400 shrink-0" />
                                  <span className="font-sans truncate max-w-[220px]">
                                    {w.title}
                                  </span>
                                  <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                                </a>
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
                              className="text-[11px] font-mono px-2 py-1 rounded hover:bg-[#2f2f2f] transition-colors flex items-center gap-1 cursor-pointer"
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
                  <div className="w-7 h-7 rounded-full bg-[#343541] border border-rose-500/50 flex items-center justify-center text-rose-400 font-bold text-xs animate-pulse">
                    <Sparkles className="w-4 h-4 text-rose-400" />
                  </div>
                  <span className="font-medium text-white text-sm">Ruby</span>
                  <span className="text-rose-400 animate-pulse font-mono">• Generating response</span>
                  {streamingSources.length > 0 && (
                    <span className="text-[11px] font-mono text-[#a1a1aa]">
                      ({streamingSources.length} document chunks)
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

                {/* Claude-style Live Activity Stepper & Thinking Box */}
                <div className="pl-9 space-y-3">
                  {(streamingSteps.length > 0 || isSearchingWeb || !!streamingThinking) && (
                    <div className="rounded-2xl bg-[#191919] border border-[#333] p-3.5 space-y-3 shadow-lg">
                      <div className="flex items-center justify-between text-xs text-[#b4b4b4] pb-2 border-b border-[#2e2e2e]">
                        <div className="flex items-center gap-2">
                          <Brain className="w-4 h-4 text-rose-400 animate-pulse" />
                          <span className="font-semibold text-white">Live Activity Trace & Thinking</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-950/80 text-rose-300 border border-rose-800/60 animate-pulse">
                            In Progress
                          </span>
                        </div>
                        <button
                          onClick={() => setIsLiveThinkingExpanded((prev) => !prev)}
                          className="text-[#888] hover:text-white transition-colors cursor-pointer"
                        >
                          {isLiveThinkingExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>

                      {isLiveThinkingExpanded && (
                        <div className="space-y-3">
                          {/* Stepper items */}
                          {streamingSteps.length > 0 && (
                            <div className="space-y-2 text-xs">
                              {streamingSteps.map((st: any) => (
                                <div key={st.id} className="flex items-start gap-2.5">
                                  {st.status === 'running' ? (
                                    <Loader2 className="w-4 h-4 text-rose-400 animate-spin shrink-0 mt-0.5" />
                                  ) : st.status === 'completed' ? (
                                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                                  ) : (
                                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                                  )}
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="font-semibold text-[#f0f0f0]">{st.label}</span>
                                      <span className="text-[10px] font-mono text-[#888] uppercase">{st.status}</span>
                                    </div>
                                    {st.description && (
                                      <p className="text-[#a1a1aa] mt-0.5 leading-relaxed">{st.description}</p>
                                    )}
                                    {st.details && Array.isArray(st.details) && (
                                      <div className="mt-1 pl-2.5 border-l-2 border-[#383838] space-y-1">
                                        {st.details.map((d: any, idx: number) => (
                                          <div key={idx} className="text-[11px] text-[#93c5fd] truncate flex items-center gap-1.5">
                                            <span className="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0" />
                                            {typeof d === 'string' ? (
                                              d
                                            ) : (
                                              <a
                                                href={d.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="hover:underline flex items-center gap-1"
                                              >
                                                <span>{d.title}</span>
                                                <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                                              </a>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Live Web Search Querying Banner */}
                          {isSearchingWeb && (
                            <div className="flex items-center gap-2 text-xs text-blue-400 bg-blue-950/40 border border-blue-800/60 p-2.5 rounded-xl animate-pulse">
                              <Globe className="w-4 h-4 animate-spin shrink-0 text-blue-400" />
                              <span>Querying SearXNG live web index for: &quot;{webSearchQuery}&quot;...</span>
                            </div>
                          )}

                          {/* Live Memory Saved Notification */}
                          {streamingMemorySaved && (
                            <div className="flex items-center gap-2 text-xs text-purple-300 bg-purple-950/40 border border-purple-800/60 p-2.5 rounded-xl">
                              <Brain className="w-4 h-4 shrink-0 text-purple-400" />
                              <span>Stored in Long-Term Memory: <strong>{streamingMemorySaved.content}</strong></span>
                            </div>
                          )}

                          {/* Live Streaming Thoughts (Internal chain of thought) */}
                          {streamingThinking && (
                            <div className="pt-2 border-t border-[#2e2e2e]">
                              <div className="text-[11px] font-mono text-rose-300 mb-1.5 flex items-center gap-1.5">
                                <Sparkles className="w-3.5 h-3.5 animate-spin text-rose-400" />
                                <span>Live AI Thinking Stream:</span>
                              </div>
                              <div className="p-3 rounded-xl bg-[#141414] border border-[#282828] text-xs font-mono text-[#a1a1aa] whitespace-pre-wrap leading-relaxed max-h-52 overflow-y-auto select-text shadow-inner">
                                {streamingThinking}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Main Streaming Output */}
                  <div className="text-[15px] leading-7 text-[#ececec]">
                    {streamingText ? (
                      <MarkdownRenderer content={streamingText} />
                    ) : (
                      <div className="text-sm text-[#8e8e8e] animate-pulse flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-rose-400" />
                        <span>Formulating academic response...</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Chat Error Card with Retry Button (Fix for Issue A) */}
            {chatError && (
              <div className="w-full pl-9">
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
                Local-first academic copilot grounded in your course materials with zero cloud leakage, SearXNG web search, and step-by-step reasoning.
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
              placeholder={`Ask anything in ${activeModeObj.name} mode...`}
              className="w-full bg-transparent text-[#ececec] placeholder:text-[#8e8e8e] text-[15px] px-3 pt-1.5 pb-1 resize-none outline-none max-h-52 overflow-y-auto leading-relaxed"
            />

            {/* Inner Bottom Controls Toolbar */}
            <div className="flex items-center justify-between px-2 pt-1">
              {/* Left: Mode / Subject / SearXNG Web Search Toggle */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {/* Subject context picker */}
                <button
                  type="button"
                  onClick={() => setSubjectPickerOpen(true)}
                  className="p-1.5 rounded-full hover:bg-[#3d3d3d] text-[#b4b4b4] hover:text-white transition-colors cursor-pointer"
                  title="Filter course context"
                >
                  <Plus className="w-4 h-4" />
                </button>

                {/* Mode Selector Pill */}
                <button
                  type="button"
                  onClick={() => {
                    const idx = CHAT_MODES.findIndex((m) => m.id === chatMode);
                    const next = CHAT_MODES[(idx + 1) % CHAT_MODES.length];
                    setChatMode(next.id);
                  }}
                  className={`px-2.5 py-1 rounded-full bg-[#242424] hover:bg-[#383838] text-[11px] font-medium text-[#b4b4b4] hover:text-white border border-[#383838] transition-colors flex items-center gap-1 cursor-pointer`}
                  title={`${activeModeObj.name}: ${activeModeObj.summary}`}
                >
                  <activeModeObj.icon className={`w-3 h-3 ${activeModeObj.color}`} />
                  <span>{activeModeObj.name}</span>
                </button>

                {/* Manual SearXNG Web Search Toggle Button */}
                <button
                  type="button"
                  onClick={() => {
                    if (chatMode !== 'web-search') {
                      setWebSearchEnabled((prev) => !prev);
                    }
                  }}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all cursor-pointer ${
                    chatMode === 'web-search' || webSearchEnabled
                      ? 'bg-sky-600/30 border-sky-500/70 text-sky-300 shadow-sm'
                      : 'bg-[#242424] border-[#383838] text-[#8e8e8e] hover:text-[#ececec]'
                  }`}
                  title={
                    chatMode === 'web-search'
                      ? 'Web Search is permanently active in Web Search Mode'
                      : webSearchEnabled
                      ? 'Web Search is ON (SearXNG). Click to disable.'
                      : 'Web Search is OFF. Click to search live web via SearXNG.'
                  }
                >
                  <Globe
                    className={`w-3 h-3 ${
                      chatMode === 'web-search' || webSearchEnabled ? 'text-sky-400' : 'text-[#8e8e8e]'
                    }`}
                  />
                  <span>{chatMode === 'web-search' ? 'Web Search (Mode)' : 'Web Search'}</span>
                  {(chatMode === 'web-search' || webSearchEnabled) && (
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400 ml-0.5" />
                  )}
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

            <div className="space-y-3">
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
                  Web results are cited with direct links <span className="font-mono text-sky-400">[Web #1]</span> so you can jump straight to external references.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#1a1a1a] border border-[#333] space-y-2">
                <h4 className="font-semibold text-white text-sm">Claude-Style Activity Trace & AI Thinking</h4>
                <p>
                  Watch real-time operational steps unfold as Ruby analyzes your query, searches course documents, executes SearXNG web queries, and validates citations. For reasoning models, the internal chain of thought streams live in a collapsible thought process box.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#1a1a1a] border border-[#333] space-y-2">
                <h4 className="font-semibold text-white text-sm">Academic Simulators & Math Engine</h4>
                <ul className="list-disc list-inside space-y-1 text-[#b4b4b4]">
                  <li><strong>SymPy Math Engine:</strong> Solves algebraic equations, derivatives, integrals, and matrix operations.</li>
                  <li><strong>Restricted Code Sandbox:</strong> Executes Python and traces algorithm steps safely with AST reflection blocking.</li>
                  <li><strong>OS & Network Simulators:</strong> Simulates CPU scheduling, Banker's deadlock avoidance, FIFO/LRU page replacement, IPv4 subnets, and logic gates.</li>
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
    </div>
  );
};
