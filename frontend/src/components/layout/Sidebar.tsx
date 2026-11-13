import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  FolderTree,
  Network,
  Brain,
  GraduationCap,
  BarChart3,
  Cpu,
  Settings,
  PanelLeftClose,
  Plus,
  Trash2,
  Edit2,
  Search,
  Check,
  X,
} from 'lucide-react';
import { HealthStatus } from '../../types';
import { ConversationItem } from '../../services/api';

interface SidebarProps {
  health?: HealthStatus;
  isLoadingHealth: boolean;
  isOpen?: boolean;
  onToggle?: () => void;
  conversations?: ConversationItem[];
  activeConvId?: string | null;
  onSelectConversation?: (id: string) => void;
  onNewChat?: () => void;
  onDeleteConversation?: (id: string) => void;
  onRenameConversation?: (id: string, title: string) => void;
}

const NAV_ITEMS = [
  { name: 'AI Chat', path: '/chat', icon: MessageSquare },
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Library', path: '/library', icon: BookOpen },
  { name: 'Subjects', path: '/subjects', icon: FolderTree },
  { name: 'Knowledge Graph', path: '/graph', icon: Network },
  { name: 'Memory Manager', path: '/memory', icon: Brain },
  { name: 'Study & Revision', path: '/study', icon: GraduationCap },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'AI Providers', path: '/providers', icon: Cpu },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({
  health,
  isLoadingHealth,
  isOpen = true,
  onToggle,
  conversations = [],
  activeConvId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onRenameConversation,
}) => {
  const isHealthy = health?.status === 'healthy';
  const location = useLocation();
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');

  if (!isOpen) {
    return null;
  }

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside className="w-[260px] h-screen bg-[#171717] border-r border-[#2f2f2f] flex flex-col justify-between select-none shrink-0 transition-all z-30">
      {/* Top Header & Actions */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Brand Header */}
        <div className="h-14 flex items-center justify-between px-3.5 border-b border-[#242424]">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-rose-600/20 border border-rose-500/30 flex items-center justify-center text-rose-400 font-bold text-sm shadow-sm">
              R
            </div>
            <div>
              <h1 className="font-semibold text-[#ececec] text-sm tracking-tight leading-none">RUBY</h1>
              <p className="text-[10px] text-[#8e8e8e] font-mono mt-0.5">Academic AI</p>
            </div>
          </div>
          {onToggle && (
            <button
              onClick={onToggle}
              className="p-1.5 text-[#b4b4b4] hover:text-white hover:bg-[#212121] rounded-lg transition-colors cursor-pointer"
              title="Close sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* ChatGPT Style "New Chat" Action Button */}
        <div className="p-3">
          <button
            onClick={() => {
              if (onNewChat) onNewChat();
            }}
            className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg border border-[#383838] bg-[#212121] hover:bg-[#282828] text-sm text-[#ececec] font-medium transition-colors cursor-pointer shadow-sm group"
          >
            <div className="flex items-center gap-2.5">
              <Plus className="w-4 h-4 text-[#ececec]" />
              <span>New chat</span>
            </div>
            <span className="text-[11px] font-mono text-[#8e8e8e] group-hover:text-[#b4b4b4]">
              Ctrl+K
            </span>
          </button>
        </div>

        {/* Scrollable Middle: Conversations & Navigation */}
        <div className="flex-1 overflow-y-auto px-3 space-y-4">
          {/* Recent Conversations */}
          {conversations.length > 0 && (
            <div className="space-y-1">
              <div className="flex items-center justify-between px-2 pt-1 pb-1 text-[11px] font-medium text-[#8e8e8e]">
                <span>Recent Chats</span>
                {conversations.length > 4 && (
                  <div className="relative flex items-center">
                    <Search className="w-3 h-3 text-[#777]" />
                  </div>
                )}
              </div>

              {conversations.length > 5 && (
                <div className="px-1 pb-1">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search chats..."
                    className="w-full bg-[#212121] border border-[#2e2e2e] rounded-md px-2.5 py-1 text-xs text-[#ececec] placeholder-[#666] focus:outline-none focus:border-[#444]"
                  />
                </div>
              )}

              <div className="space-y-0.5">
                {filteredConversations.map((c) => {
                  const isActive = activeConvId === c.id;
                  const isEditing = editingId === c.id;

                  return (
                    <div
                      key={c.id}
                      onClick={() => {
                        if (!isEditing && onSelectConversation) {
                          onSelectConversation(c.id);
                        }
                      }}
                      className={`group relative flex items-center justify-between px-2.5 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                        isActive
                          ? 'bg-[#212121] text-white font-medium shadow-sm'
                          : 'text-[#b4b4b4] hover:bg-[#212121]/60 hover:text-white'
                      }`}
                    >
                      {isEditing ? (
                        <div className="flex items-center gap-1 w-full" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="text"
                            autoFocus
                            value={editingText}
                            onChange={(e) => setEditingText(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                if (editingText.trim() && onRenameConversation) {
                                  onRenameConversation(c.id, editingText.trim());
                                }
                                setEditingId(null);
                              } else if (e.key === 'Escape') {
                                setEditingId(null);
                              }
                            }}
                            className="flex-1 bg-[#121212] border border-[#444] rounded px-1.5 py-0.5 text-xs text-white outline-none"
                          />
                          <button
                            onClick={() => {
                              if (editingText.trim() && onRenameConversation) {
                                onRenameConversation(c.id, editingText.trim());
                              }
                              setEditingId(null);
                            }}
                            className="p-1 hover:text-emerald-400"
                          >
                            <Check className="w-3 h-3" />
                          </button>
                          <button onClick={() => setEditingId(null)} className="p-1 hover:text-rose-400">
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center gap-2 truncate flex-1 min-w-0 pr-1">
                            <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70" />
                            <span className="truncate">{c.title}</span>
                          </div>
                          <div className="hidden group-hover:flex items-center gap-1 shrink-0 bg-[#212121] pl-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditingId(c.id);
                                setEditingText(c.title);
                              }}
                              className="p-1 text-[#8e8e8e] hover:text-white rounded"
                              title="Rename"
                            >
                              <Edit2 className="w-3 h-3" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onDeleteConversation) onDeleteConversation(c.id);
                              }}
                              className="p-1 text-[#8e8e8e] hover:text-rose-400 rounded"
                              title="Delete"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Academic Tools & Workspace Navigation */}
          <div className="space-y-1 pt-1 border-t border-[#242424]">
            <div className="px-2 pt-1 pb-1 text-[11px] font-medium text-[#8e8e8e]">
              <span>Academic Workspace</span>
            </div>
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path);

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-[#212121] text-white shadow-sm'
                      : 'text-[#b4b4b4] hover:bg-[#212121]/50 hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0 opacity-80" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </div>
        </div>
      </div>

      {/* Backend Health Status Badge */}
      <div className="p-3 border-t border-[#242424] bg-[#141414]">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isLoadingHealth
                  ? 'bg-amber-400 animate-pulse'
                  : isHealthy
                  ? 'bg-emerald-500 ring-2 ring-emerald-500/20'
                  : 'bg-rose-500 ring-2 ring-rose-500/20'
              }`}
            />
            <span className="font-mono text-[11px] text-[#ececec]">
              {isLoadingHealth ? 'Connecting...' : isHealthy ? 'Core Online' : 'Core Disconnected'}
            </span>
          </div>
          <span className="text-[10px] font-mono text-[#8e8e8e]">
            {health?.version ? `v${health.version}` : 'v0.1.0'}
          </span>
        </div>
      </div>
    </aside>
  );
};
