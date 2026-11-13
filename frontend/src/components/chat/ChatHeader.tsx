import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown,
  Check,
  Layers,
  Info,
  HelpCircle,
  Brain,
  Activity,
  Download,
  MoreHorizontal,
  PanelLeft,
} from 'lucide-react';

export interface ChatModeDefinition {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  borderColor: string;
  summary: string;
  whenToUse: string;
}

interface ChatHeaderProps {
  activeProvider?: any;
  providers?: any[];
  onSelectProvider?: (providerId: string) => void;
  selectedSubjectId: string;
  subjects?: any[];
  onSelectSubject: (subjectId: string) => void;
  chatMode: string;
  chatModes: ChatModeDefinition[];
  onSelectChatMode: (modeId: string) => void;
  onOpenModeHelp: () => void;
  onOpenSystemGuide: () => void;
  onOpenAgyUsage: () => void;
  onExportMarkdown: () => void;
  canExport: boolean;
  isSidebarOpen?: boolean;
  onToggleSidebar?: () => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  activeProvider,
  providers = [],
  onSelectProvider,
  selectedSubjectId,
  subjects = [],
  onSelectSubject,
  chatMode,
  chatModes,
  onSelectChatMode,
  onOpenModeHelp,
  onOpenSystemGuide,
  onOpenAgyUsage,
  onExportMarkdown,
  canExport,
  isSidebarOpen,
  onToggleSidebar,
}) => {
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [subjectDropdownOpen, setSubjectDropdownOpen] = useState(false);
  const [modeDropdownOpen, setModeDropdownOpen] = useState(false);
  const [overflowMenuOpen, setOverflowMenuOpen] = useState(false);

  const modelRef = useRef<HTMLDivElement>(null);
  const subjectRef = useRef<HTMLDivElement>(null);
  const modeRef = useRef<HTMLDivElement>(null);
  const overflowRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (modelRef.current && !modelRef.current.contains(target)) {
        setModelDropdownOpen(false);
      }
      if (subjectRef.current && !subjectRef.current.contains(target)) {
        setSubjectDropdownOpen(false);
      }
      if (modeRef.current && !modeRef.current.contains(target)) {
        setModeDropdownOpen(false);
      }
      if (overflowRef.current && !overflowRef.current.contains(target)) {
        setOverflowMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const selectedSubject = subjects.find((s: any) => s.id === selectedSubjectId);
  const activeModeObj = chatModes.find((m) => m.id === chatMode) || chatModes[0];
  const ActiveModeIcon = activeModeObj.icon;

  return (
    <header className="h-14 border-b border-[#2e2e2e] bg-[#212121]/90 backdrop-blur-md px-3.5 flex items-center justify-between shrink-0 z-20 select-none">
      {/* Left: Sidebar Toggle, Model & Subject Selectors */}
      <div className="flex items-center gap-2 min-w-0">
        {onToggleSidebar && !isSidebarOpen && (
          <button
            onClick={onToggleSidebar}
            className="p-1.5 text-[#b4b4b4] hover:text-white hover:bg-[#2c2c2c] rounded-lg transition-colors cursor-pointer mr-1"
            title="Open sidebar"
          >
            <PanelLeft className="w-4 h-4" />
          </button>
        )}

        {/* Model Selector Dropdown */}
        <div className="relative" ref={modelRef}>
          <button
            onClick={() => setModelDropdownOpen((prev) => !prev)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl hover:bg-[#2a2a2a] text-xs font-medium text-[#ececec] transition-colors cursor-pointer border border-transparent hover:border-[#383838]"
          >
            <span className="font-semibold text-white truncate max-w-[140px] sm:max-w-[180px]">
              {activeProvider?.model_name || 'Ruby 4o'}
            </span>
            {activeProvider && (
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#282828] text-[#a1a1aa] border border-[#383838]">
                {activeProvider.provider_type === 'ollama' ? 'Local' : 'Cloud'}
              </span>
            )}
            <ChevronDown className="w-3.5 h-3.5 text-[#8e8e8e]" />
          </button>

          {modelDropdownOpen && (
            <div className="absolute left-0 top-full mt-1.5 w-72 rounded-xl bg-[#252525] border border-[#383838] shadow-2xl p-2 z-50 text-xs">
              <div className="px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider text-[#8e8e8e]">
                AI Models & Providers
              </div>
              <div className="space-y-1 mt-1 max-h-60 overflow-y-auto">
                {providers.map((p: any) => (
                  <div
                    key={p.id}
                    onClick={() => {
                      if (onSelectProvider) onSelectProvider(p.id);
                      setModelDropdownOpen(false);
                    }}
                    className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                      p.is_default
                        ? 'bg-[#333333] text-white font-medium'
                        : 'text-[#b4b4b4] hover:bg-[#2c2c2c] hover:text-white'
                    }`}
                  >
                    <div className="truncate mr-2">
                      <div className="text-xs text-[#ececec] truncate">{p.model_name}</div>
                      <div className="text-[10px] text-[#8e8e8e] capitalize font-mono">
                        {p.provider_type} {p.provider_type === 'ollama' && '• Private'}
                      </div>
                    </div>
                    {p.is_default && <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Subject Filter Dropdown */}
        <div className="relative hidden sm:block" ref={subjectRef}>
          <button
            onClick={() => setSubjectDropdownOpen((prev) => !prev)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-[#333333] bg-[#262626] hover:bg-[#2c2c2c] text-xs text-[#b4b4b4] hover:text-white transition-colors cursor-pointer"
          >
            <Layers className="w-3.5 h-3.5 text-[#8e8e8e]" />
            <span className="max-w-[110px] md:max-w-[140px] truncate">
              {selectedSubject ? selectedSubject.name : 'All Subjects'}
            </span>
            <ChevronDown className="w-3 h-3 text-[#8e8e8e]" />
          </button>

          {subjectDropdownOpen && (
            <div className="absolute left-0 top-full mt-1.5 w-60 rounded-xl bg-[#252525] border border-[#383838] shadow-2xl p-1.5 z-50 text-xs">
              <button
                onClick={() => {
                  onSelectSubject('');
                  setSubjectDropdownOpen(false);
                }}
                className={`w-full text-left p-2 rounded-lg transition-colors ${
                  !selectedSubjectId
                    ? 'bg-[#333333] text-white font-medium'
                    : 'text-[#b4b4b4] hover:bg-[#2c2c2c]'
                }`}
              >
                All Course Context
              </button>
              <div className="space-y-0.5 mt-1 max-h-52 overflow-y-auto">
                {subjects.map((s: any) => (
                  <button
                    key={s.id}
                    onClick={() => {
                      onSelectSubject(s.id);
                      setSubjectDropdownOpen(false);
                    }}
                    className={`w-full text-left p-2 rounded-lg truncate transition-colors ${
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
          )}
        </div>
      </div>

      {/* Right: Mode Selector Pill & Action Buttons */}
      <div className="flex items-center gap-1.5">
        {/* Chat Mode Dropdown Pill */}
        <div className="relative" ref={modeRef}>
          <div className="flex items-center bg-[#262626] p-0.5 rounded-xl border border-[#333333]">
            <button
              onClick={() => setModeDropdownOpen((prev) => !prev)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-white hover:bg-[#2e2e2e] transition-colors cursor-pointer"
            >
              <ActiveModeIcon className={`w-3.5 h-3.5 ${activeModeObj.color}`} />
              <span className="font-medium">{activeModeObj.name}</span>
              <ChevronDown className="w-3 h-3 text-[#8e8e8e]" />
            </button>

            <button
              onClick={onOpenModeHelp}
              className="p-1 text-[#8e8e8e] hover:text-white rounded-lg hover:bg-[#333333] transition-colors"
              title="Learn about Chat Modes"
            >
              <Info className="w-3.5 h-3.5" />
            </button>
          </div>

          {modeDropdownOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-72 rounded-xl bg-[#252525] border border-[#383838] shadow-2xl p-2 z-50 text-xs">
              <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-[#8e8e8e]">
                Select Mode
              </div>
              <div className="space-y-1 mt-1">
                {chatModes.map((m) => {
                  const Icon = m.icon;
                  const isActive = chatMode === m.id;
                  return (
                    <div
                      key={m.id}
                      onClick={() => {
                        onSelectChatMode(m.id);
                        setModeDropdownOpen(false);
                      }}
                      className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                        isActive
                          ? 'bg-[#333333] text-white'
                          : 'text-[#b4b4b4] hover:bg-[#2c2c2c] hover:text-white'
                      }`}
                    >
                      <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${m.color}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-xs text-[#ececec]">{m.name}</span>
                          {isActive && <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
                        </div>
                        <p className="text-[11px] text-[#8e8e8e] line-clamp-1 mt-0.5">
                          {m.summary}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Primary Desktop Action Buttons */}
        <div className="hidden lg:flex items-center gap-1">
          {/* AGY Quotas */}
          <button
            onClick={onOpenAgyUsage}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[#b4b4b4] hover:text-indigo-300 hover:bg-[#2a2a2a] transition-colors cursor-pointer"
            title="AGY Quotas & Usage Dashboard"
          >
            <Activity className="w-3.5 h-3.5 text-indigo-400" />
            <span>AGY Quotas</span>
          </button>

          {/* Memories */}
          <Link
            to="/memory"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[#b4b4b4] hover:text-purple-300 hover:bg-[#2a2a2a] transition-colors"
            title="Memory Manager"
          >
            <Brain className="w-3.5 h-3.5 text-purple-400" />
            <span>Memories</span>
          </Link>

          {/* Guide */}
          <button
            onClick={onOpenSystemGuide}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-[#b4b4b4] hover:text-white hover:bg-[#2a2a2a] transition-colors cursor-pointer"
            title="System Guide"
          >
            <HelpCircle className="w-3.5 h-3.5 text-rose-400" />
            <span>Guide</span>
          </button>

          {/* Export Markdown */}
          {canExport && (
            <button
              onClick={onExportMarkdown}
              className="p-1.5 text-[#b4b4b4] hover:text-white hover:bg-[#2a2a2a] rounded-lg transition-colors cursor-pointer"
              title="Export chat as Markdown"
            >
              <Download className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Responsive Overflow Menu for Smaller Screens */}
        <div className="relative lg:hidden" ref={overflowRef}>
          <button
            onClick={() => setOverflowMenuOpen((prev) => !prev)}
            className="p-1.5 text-[#b4b4b4] hover:text-white hover:bg-[#2a2a2a] rounded-lg transition-colors cursor-pointer"
            title="More actions"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {overflowMenuOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-48 rounded-xl bg-[#252525] border border-[#383838] shadow-2xl p-1.5 z-50 text-xs space-y-0.5">
              <button
                onClick={() => {
                  onOpenAgyUsage();
                  setOverflowMenuOpen(false);
                }}
                className="w-full flex items-center gap-2 p-2 rounded-lg text-[#b4b4b4] hover:text-white hover:bg-[#2e2e2e] transition-colors text-left"
              >
                <Activity className="w-4 h-4 text-indigo-400" />
                <span>AGY Quotas</span>
              </button>

              <Link
                to="/memory"
                onClick={() => setOverflowMenuOpen(false)}
                className="w-full flex items-center gap-2 p-2 rounded-lg text-[#b4b4b4] hover:text-white hover:bg-[#2e2e2e] transition-colors text-left"
              >
                <Brain className="w-4 h-4 text-purple-400" />
                <span>Memory Manager</span>
              </Link>

              <button
                onClick={() => {
                  onOpenSystemGuide();
                  setOverflowMenuOpen(false);
                }}
                className="w-full flex items-center gap-2 p-2 rounded-lg text-[#b4b4b4] hover:text-white hover:bg-[#2e2e2e] transition-colors text-left"
              >
                <HelpCircle className="w-4 h-4 text-rose-400" />
                <span>System Guide</span>
              </button>

              {canExport && (
                <button
                  onClick={() => {
                    onExportMarkdown();
                    setOverflowMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2 p-2 rounded-lg text-[#b4b4b4] hover:text-white hover:bg-[#2e2e2e] transition-colors text-left border-t border-[#333333] pt-1.5"
                >
                  <Download className="w-4 h-4 text-emerald-400" />
                  <span>Export Chat (.md)</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
