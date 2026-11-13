import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';
import { Header } from '../components/layout/Header';
import { HealthStatus } from '../types';

describe('Sidebar Navigation', () => {
  it('renders brand name and all 10 core navigation links', () => {
    const mockHealth: HealthStatus = {
      status: 'healthy',
      app_name: 'Ruby',
      version: '0.1.0',
      environment: 'development',
      database_connected: true,
      storage_accessible: true,
      data_directory: '/tmp/ruby/data',
      timestamp: new Date().toISOString(),
    };

    render(
      <MemoryRouter>
        <Sidebar health={mockHealth} isLoadingHealth={false} />
      </MemoryRouter>
    );

    expect(screen.getByText('RUBY')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('AI Chat')).toBeInTheDocument();
    expect(screen.getByText('Library')).toBeInTheDocument();
    expect(screen.getByText('Subjects')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument();
    expect(screen.getByText('Memory Manager')).toBeInTheDocument();
    expect(screen.getByText('Study & Revision')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('AI Providers')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.getByText('Core Online')).toBeInTheDocument();
  });
});

describe('Header Component', () => {
  it('displays local environment badge and privacy status', () => {
    const mockHealth: HealthStatus = {
      status: 'healthy',
      app_name: 'Ruby',
      version: '0.1.0',
      environment: 'development',
      database_connected: true,
      storage_accessible: true,
      data_directory: '/tmp/ruby/data',
      timestamp: new Date().toISOString(),
    };

    render(<Header health={mockHealth} />);
    expect(screen.getByText('Local Environment')).toBeInTheDocument();
    expect(screen.getByText('Local First & Private')).toBeInTheDocument();
    expect(screen.getByText('SQLite Connected')).toBeInTheDocument();
  });
});
