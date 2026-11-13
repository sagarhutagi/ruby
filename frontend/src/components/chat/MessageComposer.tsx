import React, { useRef, useEffect } from 'react';
import { ArrowUp, Square, Globe, Plus } from 'lucide-react';
import { ChatModeDefinition } from './ChatHeader';

interface MessageComposerProps {
  inputText: string;
  onChangeText: (text: string) => void;
  onSendMessage: (prompt?: string) => void;
  isStreaming: boolean;
  onStopStream: () => void;
  chatMode: string;
  chatModes: ChatModeDefinition[];
  onChangeChatMode: (modeId: string) => void;
  webSearchEnabled: boolean;
  onToggleWebSearch: () => void;
  onOpenSubjectPicker: () => void;
  selectedSubjectName?: string;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  inputText,
  onChangeText,
  onSendMessage,
  isStreaming,
  onStopStream,
  chatMode,
  chatModes,
  onChangeChatMode,
  webSearchEnabled,
  onToggleWebSearch,
  onOpenSubjectPicker,
  selectedSubjectName,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea like ChatGPT
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputText]);

  const activeModeObj = chatModes.find((m) => m.id === chatMode) || chatModes[0];
  const ActiveIcon = activeModeObj.icon;
  const isWebSearchActive = chatMode === 'web-search' || webSearchEnabled;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && inputText.trim()) {
        onSendMessage();
      }
    }
  };

  const cycleMode = () => {
    const idx = chatModes.findIndex((m) => m.id === chatMode);
    const next = chatModes[(idx + 1) % chatModes.length];
    onChangeChatMode(next.id);
  };

  return (
    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#212121] via-[#212121]/95 to-transparent pt-6 pb-4 px-4 z-20">
      <div className="max-w-4xl mx-auto w-full">
        {/* Capsule Container */}
        <div className="rounded-[26px] bg-[#2a2a2a] border border-[#383838] focus-within:border-[#555] shadow-2xl p-2.5 flex flex-col transition-all">
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={(e) => onChangeText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask anything in ${activeModeObj.name} mode... (Shift+Enter for newline)`}
            className="w-full bg-transparent text-[#ececec] placeholder:text-[#8e8e8e] text-[15px] px-3 pt-1.5 pb-1 resize-none outline-none max-h-52 overflow-y-auto leading-relaxed"
          />

          {/* Bottom Controls Bar */}
          <div className="flex items-center justify-between px-2 pt-1.5 flex-wrap gap-2">
            {/* Left Controls: Subject context, Mode Switcher, Web Search Toggle */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {/* Context / Subject Pill */}
              <button
                type="button"
                onClick={onOpenSubjectPicker}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#222222] hover:bg-[#333333] text-[11px] font-medium text-[#b4b4b4] hover:text-white border border-[#383838] transition-colors cursor-pointer"
                title={selectedSubjectName ? `Context: ${selectedSubjectName}` : 'Add course context'}
              >
                <Plus className="w-3.5 h-3.5" />
                <span className="max-w-[120px] truncate">
                  {selectedSubjectName || 'Context'}
                </span>
              </button>

              {/* Mode Switcher Pill */}
              <button
                type="button"
                onClick={cycleMode}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#222222] hover:bg-[#333333] text-[11px] font-medium text-[#b4b4b4] hover:text-white border border-[#383838] transition-colors cursor-pointer"
                title={`${activeModeObj.name}: ${activeModeObj.summary} (Click to switch)`}
              >
                <ActiveIcon className={`w-3 h-3 ${activeModeObj.color}`} />
                <span>{activeModeObj.name}</span>
              </button>

              {/* Web Search Toggle */}
              <button
                type="button"
                onClick={() => {
                  if (chatMode !== 'web-search') {
                    onToggleWebSearch();
                  }
                }}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all cursor-pointer ${
                  isWebSearchActive
                    ? 'bg-sky-600/25 border-sky-500/60 text-sky-300 shadow-sm'
                    : 'bg-[#222222] border-[#383838] text-[#8e8e8e] hover:text-[#ececec]'
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
                  className={`w-3 h-3 ${isWebSearchActive ? 'text-sky-400' : 'text-[#8e8e8e]'}`}
                />
                <span>{chatMode === 'web-search' ? 'Web Search (Mode)' : 'Web Search'}</span>
                {isWebSearchActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-400 ml-0.5" />
                )}
              </button>
            </div>

            {/* Right Action: Send / Stop Button */}
            <div>
              {isStreaming ? (
                <button
                  type="button"
                  onClick={onStopStream}
                  className="w-8 h-8 rounded-full bg-white text-black hover:bg-neutral-200 flex items-center justify-center cursor-pointer shadow-md transition-transform active:scale-95"
                  title="Stop generating"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                </button>
              ) : (
                <button
                  type="button"
                  disabled={!inputText.trim()}
                  onClick={() => onSendMessage()}
                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                    inputText.trim()
                      ? 'bg-white text-black hover:bg-neutral-200 cursor-pointer shadow-md active:scale-95'
                      : 'bg-[#3e3e3e] text-[#8e8e8e] cursor-not-allowed opacity-50'
                  }`}
                  title="Send message (Enter)"
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
  );
};
