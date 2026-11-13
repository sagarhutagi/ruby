import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { LibraryPage } from './pages/LibraryPage';
import { SubjectsPage } from './pages/SubjectsPage';
import { KnowledgeGraphPage } from './pages/KnowledgeGraphPage';
import { MemoryPage } from './pages/MemoryPage';
import { StudyPage } from './pages/StudyPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { ProvidersPage } from './pages/ProvidersPage';
import { SettingsPage } from './pages/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="library" element={<LibraryPage />} />
            <Route path="subjects" element={<SubjectsPage />} />
            <Route path="graph" element={<KnowledgeGraphPage />} />
            <Route path="memory" element={<MemoryPage />} />
            <Route path="study" element={<StudyPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="providers" element={<ProvidersPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
