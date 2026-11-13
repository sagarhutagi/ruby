import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import {
  fetchHealth,
  fetchConversations,
  deleteConversation,
  updateConversation,
} from '../../services/api';

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const activeConvId = searchParams.get('c');

  const { data: health, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 10000,
  });

  const { data: conversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => fetchConversations(),
  });

  const deleteConvMutation = useMutation({
    mutationFn: (id: string) => deleteConversation(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (activeConvId === deletedId) {
        navigate('/chat');
      }
    },
  });

  const updateTitleMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      updateConversation(id, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  const isChat = location.pathname === '/chat';

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#212121] text-[#ececec]">
      <Sidebar
        health={health}
        isLoadingHealth={isLoading}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen((prev) => !prev)}
        conversations={conversations || []}
        activeConvId={activeConvId}
        onNewChat={() => {
          navigate('/chat');
        }}
        onSelectConversation={(id) => {
          navigate(`/chat?c=${id}`);
        }}
        onDeleteConversation={(id) => deleteConvMutation.mutate(id)}
        onRenameConversation={(id, title) => updateTitleMutation.mutate({ id, title })}
      />
      <div className="flex flex-col flex-1 h-screen overflow-hidden bg-[#212121]">
        <Header
          health={health}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        />
        <main
          className={`flex-1 overflow-hidden bg-[#212121] ${
            isChat ? 'p-0 flex flex-col' : 'overflow-y-auto p-6'
          }`}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
};
