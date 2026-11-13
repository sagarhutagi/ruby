import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { KnowledgeGraphPage } from '../pages/KnowledgeGraphPage';

// Mock ResizeObserver for React Flow in test environment
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('KnowledgeGraphPage Component', () => {
  it('renders graph header, filters, and action buttons', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <KnowledgeGraphPage />
      </QueryClientProvider>
    );

    expect(screen.getByText('Academic Knowledge Graph & Vault Explorer')).toBeInTheDocument();
    expect(screen.getByText('Add Concept')).toBeInTheDocument();
    expect(screen.getByText('Connect')).toBeInTheDocument();
    expect(screen.getByText('Auto-Extract')).toBeInTheDocument();
    expect(screen.getByText('Obsidian Vault')).toBeInTheDocument();
    expect(screen.getByText('Verified only')).toBeInTheDocument();
  });
});
