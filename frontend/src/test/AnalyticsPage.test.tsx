import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnalyticsPage } from '../pages/AnalyticsPage';

const createTestQueryClient = () => {
  const qc = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  qc.setQueryData(['analytics-overview'], {
    documents: {
      total_documents: 5,
      total_storage_bytes: 50000,
      total_storage_mb: 0.05,
      total_chunks: 10,
      by_file_type: { pdf: 3, markdown: 2 },
      by_status: { indexed: 5 },
      by_subject: { 'Operating Systems': 5 },
    },
    study: {
      flashcards: {
        total_cards: 12,
        total_reviews: 4,
        average_stability_days: 10,
        average_difficulty: 5,
        ratings_distribution: { Good: 3, Easy: 1 },
      },
      quizzes: {
        total_quizzes_taken: 3,
        average_score_percentage: 85,
        total_questions_answered: 15,
        correct_answers: 13,
        accuracy_percentage: 86.7,
      },
      study_time: { total_sessions: 2, total_minutes: 60, total_hours: 1 },
      knowledge_graph: { total_concepts: 20, verified_concepts: 15, ai_suggested_concepts: 5 },
    },
    tokens: {
      total_messages: 8,
      total_tokens_consumed: 4000,
      total_estimated_cost_usd: 0.0,
      by_provider: {},
      by_model: {},
      by_mode: {},
    },
  });
  return qc;
};

describe('AnalyticsPage Component', () => {
  it('renders analytics header and 5 primary tabs', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <AnalyticsPage />
      </QueryClientProvider>
    );

    expect(screen.getByText('Analytics & System Diagnostics')).toBeInTheDocument();
    expect(screen.getByText('Hardware Telemetry')).toBeInTheDocument();
    expect(screen.getByText('Study & Retention')).toBeInTheDocument();
    expect(screen.getByText('Library & Documents')).toBeInTheDocument();
    expect(screen.getByText('AI Tokens & Cost')).toBeInTheDocument();
    expect(screen.getByText('System Diagnostics & Audit')).toBeInTheDocument();
  });

  it('navigates between analytics tabs smoothly', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <AnalyticsPage />
      </QueryClientProvider>
    );

    // Switch to Study Tab
    fireEvent.click(screen.getByText('Study & Retention'));
    expect(screen.getByText('Flashcards in Decks')).toBeInTheDocument();

    // Switch to Library Tab
    fireEvent.click(screen.getByText('Library & Documents'));
    expect(screen.getByText('Indexed Documents')).toBeInTheDocument();

    // Switch to Tokens Tab
    fireEvent.click(screen.getByText('AI Tokens & Cost'));
    expect(screen.getByText('Tokens Tracked')).toBeInTheDocument();

    // Switch to Diagnostics Tab
    fireEvent.click(screen.getByText('System Diagnostics & Audit'));
    expect(screen.getByText('Export Sanitized Report')).toBeInTheDocument();
  });
});
