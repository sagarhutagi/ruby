import React, { useState } from 'react';
import {
  Brain,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Sparkles,
  ExternalLink,
  ShieldAlert,
  Check,
  X,
  Clock,
  Terminal,
  Database,
} from 'lucide-react';
import { replyPermission } from '../../services/api';

export interface TimelineStep {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'needs_approval';
  description?: string;
  details?: any[];
  duration_ms?: number;
  tool_name?: string;
  tool_input?: Record<string, any>;
  tool_output?: any;
  permission_request_id?: string;
  subtasks?: TimelineStep[];
}

interface ExecutionTimelineProps {
  steps?: TimelineStep[];
  thinkingContent?: string;
  isLive?: boolean;
  autoModeExplanation?: string;
  recalledMemoriesCount?: number;
  newMemoriesCount?: number;
  totalDurationMs?: number;
  defaultExpanded?: boolean;
  onPermissionResolved?: (requestId: string, approved: boolean) => void;
}

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({
  steps = [],
  thinkingContent = '',
  isLive = false,
  autoModeExplanation,
  recalledMemoriesCount,
  newMemoriesCount,
  totalDurationMs,
  defaultExpanded = false,
  onPermissionResolved,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded || isLive);
  const [resolvingPermId, setResolvingPermId] = useState<string | null>(null);
  const [resolvedPermissions, setResolvedPermissions] = useState<Record<string, boolean>>({});
  const [rememberChoice, setRememberChoice] = useState<boolean>(false);

  const hasSteps = steps.length > 0;
  const hasThinking = !!thinkingContent;
  const hasContent = hasSteps || hasThinking || !!autoModeExplanation || !!recalledMemoriesCount;

  if (!hasContent) return null;

  const handleApproveDeny = async (requestId: string, approved: boolean) => {
    setResolvingPermId(requestId);
    try {
      await replyPermission(requestId, approved, rememberChoice);
      setResolvedPermissions((prev) => ({ ...prev, [requestId]: approved }));
      if (onPermissionResolved) {
        onPermissionResolved(requestId, approved);
      }
    } catch (e) {
      console.error('Failed to resolve permission request:', e);
    } finally {
      setResolvingPermId(null);
    }
  };

  const completedStepsCount = steps.filter((s) => s.status === 'completed').length;

  return (
    <div className="mb-3.5">
      {/* Compact Trigger Button */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setIsExpanded((prev) => !prev)}
          className={`flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-xl border transition-all cursor-pointer shadow-sm group ${
            isLive
              ? 'bg-[#262626] border-rose-500/40 text-[#ececec] hover:border-rose-400'
              : 'bg-[#242424] hover:bg-[#2c2c2c] border-[#363636] text-[#b4b4b4] hover:text-white'
          }`}
        >
          <Brain
            className={`w-3.5 h-3.5 transition-transform group-hover:scale-110 ${
              isLive ? 'text-rose-400 animate-pulse' : 'text-rose-400'
            }`}
          />
          <span>
            {hasThinking && hasSteps
              ? 'Thought Process & Steps'
              : hasThinking
              ? 'Thought Process'
              : 'Execution Activity'}
            {steps.length > 0 && ` (${completedStepsCount}/${steps.length})`}
          </span>

          {totalDurationMs !== undefined && (
            <span className="text-[10px] font-mono text-[#8e8e8e] ml-1">
              {totalDurationMs}ms
            </span>
          )}

          {isLive && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-rose-950/80 text-rose-300 border border-rose-800/60 animate-pulse">
              Running
            </span>
          )}

          {isExpanded ? (
            <ChevronUp className="w-3.5 h-3.5 text-[#888] ml-0.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-[#888] ml-0.5" />
          )}
        </button>

        {autoModeExplanation && (
          <span className="text-[11px] text-indigo-300 bg-indigo-950/40 border border-indigo-800/40 px-2 py-0.5 rounded-lg flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-indigo-400 shrink-0" />
            <span className="truncate max-w-[280px]">{autoModeExplanation}</span>
          </span>
        )}

        {recalledMemoriesCount !== undefined && recalledMemoriesCount > 0 && (
          <span className="text-[11px] text-purple-300 bg-purple-950/40 border border-purple-800/40 px-2 py-0.5 rounded-lg flex items-center gap-1 font-mono">
            <Database className="w-3 h-3 text-purple-400 shrink-0" />
            <span>{recalledMemoriesCount} memories recalled</span>
          </span>
        )}

        {newMemoriesCount !== undefined && newMemoriesCount > 0 && (
          <span className="text-[11px] text-emerald-300 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded-lg flex items-center gap-1 font-mono">
            <Database className="w-3 h-3 text-emerald-400 shrink-0" />
            <span>+{newMemoriesCount} new memory</span>
          </span>
        )}
      </div>

      {/* Expanded Timeline Panel */}
      {isExpanded && (
        <div className="mt-2.5 p-3.5 rounded-2xl bg-[#191919] border border-[#333333] space-y-3.5 shadow-inner">
          {/* Timeline Step Items */}
          {steps.length > 0 && (
            <div className="space-y-3 text-xs">
              {steps.map((st, idx) => {
                const isNeedsApproval =
                  st.status === 'needs_approval' || (st.permission_request_id && resolvedPermissions[st.permission_request_id] === undefined);
                const isApproved =
                  st.permission_request_id && resolvedPermissions[st.permission_request_id] === true;
                const isDenied =
                  st.permission_request_id && resolvedPermissions[st.permission_request_id] === false;

                return (
                  <div key={st.id || idx} className="space-y-2">
                    <div className="flex items-start gap-2.5">
                      {/* Status Icon */}
                      <div className="mt-0.5 shrink-0">
                        {isNeedsApproval ? (
                          <ShieldAlert className="w-4 h-4 text-amber-400 animate-bounce" />
                        ) : st.status === 'completed' || isApproved ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : st.status === 'failed' || isDenied ? (
                          <AlertTriangle className="w-4 h-4 text-rose-400" />
                        ) : (
                          <Loader2 className="w-4 h-4 text-rose-400 animate-spin" />
                        )}
                      </div>

                      {/* Step Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-[#f0f0f0] tracking-tight">
                            {st.label}
                          </span>
                          <div className="flex items-center gap-1.5 shrink-0">
                            {st.duration_ms !== undefined && (
                              <span className="text-[10px] font-mono text-[#71717a] flex items-center gap-0.5">
                                <Clock className="w-2.5 h-2.5" />
                                {st.duration_ms}ms
                              </span>
                            )}
                            <span
                              className={`text-[10px] font-mono uppercase px-1.5 py-0.2 rounded ${
                                st.status === 'completed'
                                  ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-800/50'
                                  : st.status === 'running'
                                  ? 'bg-rose-950/70 text-rose-300 border border-rose-800/50 animate-pulse'
                                  : st.status === 'needs_approval'
                                  ? 'bg-amber-950/80 text-amber-300 border border-amber-700/60'
                                  : 'bg-[#2a2a2a] text-[#8e8e8e]'
                              }`}
                            >
                              {isNeedsApproval ? 'Action Required' : st.status}
                            </span>
                          </div>
                        </div>

                        {st.description && (
                          <p className="text-[#a1a1aa] mt-0.5 leading-relaxed">
                            {st.description}
                          </p>
                        )}

                        {/* Interactive Permission Request Gate */}
                        {isNeedsApproval && st.permission_request_id && (
                          <div className="mt-2.5 p-3 rounded-xl bg-amber-950/30 border border-amber-700/50 text-xs space-y-2.5 shadow-sm">
                            <div className="flex items-center gap-2 text-amber-300 font-semibold">
                              <ShieldAlert className="w-4 h-4" />
                              <span>Tool Execution Permission Requested</span>
                            </div>
                            <p className="text-[#d4d4d8]">
                              Ruby needs your approval to execute tool{' '}
                              <strong className="text-white font-mono bg-[#282828] px-1.5 py-0.5 rounded border border-[#383838]">
                                {st.tool_name || 'external_action'}
                              </strong>
                              .
                            </p>
                            {st.tool_input && (
                              <div className="p-2 rounded-lg bg-[#141414] border border-[#2d2d2d] font-mono text-[11px] text-[#93c5fd] overflow-x-auto">
                                {JSON.stringify(st.tool_input, null, 2)}
                              </div>
                            )}
                            <div className="flex items-center justify-between pt-1">
                              <label className="flex items-center gap-1.5 text-[11px] text-[#a1a1aa] cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={rememberChoice}
                                  onChange={(e) => setRememberChoice(e.target.checked)}
                                  className="rounded border-[#444] bg-[#222] text-rose-500"
                                />
                                <span>Remember my choice for this tool</span>
                              </label>

                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() =>
                                    handleApproveDeny(st.permission_request_id!, false)
                                  }
                                  disabled={resolvingPermId === st.permission_request_id}
                                  className="px-2.5 py-1 rounded-lg bg-[#2e2e2e] hover:bg-[#383838] text-rose-400 hover:text-rose-300 border border-rose-900/40 text-xs font-medium transition-colors flex items-center gap-1 cursor-pointer"
                                >
                                  <X className="w-3.5 h-3.5" />
                                  <span>Deny</span>
                                </button>
                                <button
                                  onClick={() =>
                                    handleApproveDeny(st.permission_request_id!, true)
                                  }
                                  disabled={resolvingPermId === st.permission_request_id}
                                  className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors flex items-center gap-1 cursor-pointer shadow"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                  <span>Allow Execution</span>
                                </button>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Resolved Permission Banner */}
                        {isApproved && (
                          <div className="mt-1 text-[11px] text-emerald-400 flex items-center gap-1">
                            <Check className="w-3 h-3" />
                            <span>Execution approved by user</span>
                          </div>
                        )}
                        {isDenied && (
                          <div className="mt-1 text-[11px] text-rose-400 flex items-center gap-1">
                            <X className="w-3 h-3" />
                            <span>Execution denied by user</span>
                          </div>
                        )}

                        {/* Tool input / output summary badge */}
                        {st.tool_name && !isNeedsApproval && (
                          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] font-mono text-[#a1a1aa]">
                            <Terminal className="w-3 h-3 text-teal-400" />
                            <span>tool: {st.tool_name}</span>
                          </div>
                        )}

                        {/* Details (e.g. nested links or query titles) */}
                        {st.details && Array.isArray(st.details) && st.details.length > 0 && (
                          <div className="mt-1.5 pl-2.5 border-l-2 border-[#383838] space-y-1">
                            {st.details.map((d, dIdx) => (
                              <div
                                key={dIdx}
                                className="text-[11px] text-[#93c5fd] truncate flex items-center gap-1.5"
                              >
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

                        {/* Nested Subtasks (Hierarchical DAG support) */}
                        {st.subtasks && st.subtasks.length > 0 && (
                          <div className="mt-2 pl-3 border-l-2 border-indigo-700/40 space-y-2">
                            {st.subtasks.map((sub, sIdx) => (
                              <div key={sub.id || sIdx} className="flex items-center gap-2">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                                <span className="text-[11px] text-[#d4d4d8]">{sub.label}</span>
                                {sub.duration_ms && (
                                  <span className="text-[10px] font-mono text-[#71717a]">
                                    ({sub.duration_ms}ms)
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* AI Internal Chain of Thought Box */}
          {hasThinking && (
            <div className="pt-2.5 border-t border-[#2e2e2e]">
              <div className="text-[11px] font-mono text-rose-300 mb-1.5 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-rose-400" />
                <span>Internal Chain of Thought:</span>
              </div>
              <div className="p-3 rounded-xl bg-[#141414] border border-[#2a2a2a] text-xs font-mono text-[#a1a1aa] whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto select-text shadow-inner">
                {thinkingContent}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
