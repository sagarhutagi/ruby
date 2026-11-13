import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StudyPage } from '../pages/StudyPage';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('StudyPage Component', () => {
  it('renders page header and navigation tabs', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <StudyPage />
      </QueryClientProvider>
    );

    expect(screen.getByText('Academic Intelligence & Study Hub')).toBeInTheDocument();
    expect(screen.getByText('FSRS Flashcards')).toBeInTheDocument();
    expect(screen.getByText('Quizzes & Mock Exams')).toBeInTheDocument();
    expect(screen.getByText('Academic Simulators & Sandbox')).toBeInTheDocument();
  });

  it('switches between flashcards, quizzes, and simulators tabs', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <StudyPage />
      </QueryClientProvider>
    );

    // Initial state: Flashcards
    expect(screen.getByText('FSRS Spaced Repetition Decks')).toBeInTheDocument();

    // Switch to Quizzes
    fireEvent.click(screen.getByText('Quizzes & Mock Exams'));
    expect(screen.getByText('Academic Quizzes & Mock Examinations')).toBeInTheDocument();

    // Switch to Simulators
    fireEvent.click(screen.getByText('Academic Simulators & Sandbox'));
    expect(screen.getByText('SymPy Symbolic Mathematics Engine')).toBeInTheDocument();
  });
});
