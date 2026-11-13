import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { WebSourceCard, WebSourceGrid } from '../components/chat/WebSourceCard';
import { ExecutionTimeline, TimelineStep } from '../components/chat/ExecutionTimeline';
import { ChatHeader, ChatModeDefinition } from '../components/chat/ChatHeader';
import { MessageComposer } from '../components/chat/MessageComposer';
import { Sparkles, Shield } from 'lucide-react';

describe('WebSourceCard & WebSourceGrid', () => {
  it('renders web source domain, title, snippet, and link', () => {
    const mockSource = {
      title: 'Jensen Huang Keynote 2026',
      url: 'https://news.nvidia.com/press-releases/2026/blackwell-orders',
      snippet: 'NVIDIA CEO Jensen Huang announces $1 trillion in enterprise orders.',
      published_date: 'Jan 2026',
    };

    render(<WebSourceCard source={mockSource} index={0} />);

    expect(screen.getByText('Jensen Huang Keynote 2026')).toBeInTheDocument();
    expect(screen.getByText('news.nvidia.com')).toBeInTheDocument();
    expect(screen.getByText(/NVIDIA CEO Jensen Huang/)).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
  });

  it('renders grid with multiple sources and expand toggle', () => {
    const sources = Array.from({ length: 6 }, (_, i) => ({
      title: `Source Title ${i + 1}`,
      url: `https://example.com/source-${i + 1}`,
      snippet: `Snippet for source ${i + 1}`,
    }));

    render(<WebSourceGrid sources={sources} />);

    expect(screen.getByText(/Web Sources/)).toBeInTheDocument();
    expect(screen.getByText('(6)')).toBeInTheDocument();
    expect(screen.getByText('+2 more')).toBeInTheDocument();

    fireEvent.click(screen.getByText('+2 more'));
    expect(screen.getByText('Show fewer')).toBeInTheDocument();
  });
});

describe('ExecutionTimeline', () => {
  it('renders timeline with steps, durations, and thought process', () => {
    const mockSteps: TimelineStep[] = [
      {
        id: 's1',
        label: 'Mode Routed: Grounded',
        status: 'completed',
        duration_ms: 120,
      },
      {
        id: 's2',
        label: 'Vector Retrieval',
        status: 'completed',
        duration_ms: 450,
      },
    ];

    render(
      <ExecutionTimeline
        steps={mockSteps}
        thinkingContent="Evaluating student query against OS paging syllabus..."
        totalDurationMs={570}
        defaultExpanded={true}
      />
    );

    expect(screen.getByText(/Thought Process & Steps/)).toBeInTheDocument();
    expect(screen.getByText('Mode Routed: Grounded')).toBeInTheDocument();
    expect(screen.getByText('Vector Retrieval')).toBeInTheDocument();
    expect(screen.getByText('Internal Chain of Thought:')).toBeInTheDocument();
    expect(screen.getByText(/Evaluating student query/)).toBeInTheDocument();
  });

  it('renders interactive tool permission request gate', () => {
    const mockSteps: TimelineStep[] = [
      {
        id: 'perm-step',
        label: 'Code Sandbox Execution',
        status: 'needs_approval',
        tool_name: 'execute_python',
        tool_input: { code: "print('safe execution')" },
        permission_request_id: 'req-1234',
      },
    ];

    render(
      <ExecutionTimeline
        steps={mockSteps}
        defaultExpanded={true}
      />
    );

    expect(screen.getByText(/Tool Execution Permission Requested/)).toBeInTheDocument();
    expect(screen.getByText('execute_python')).toBeInTheDocument();
    expect(screen.getByText('Allow Execution')).toBeInTheDocument();
    expect(screen.getByText('Deny')).toBeInTheDocument();
  });
});

describe('ChatHeader', () => {
  const mockModes: ChatModeDefinition[] = [
    {
      id: 'auto',
      name: 'Auto',
      icon: Sparkles,
      color: 'text-indigo-400',
      borderColor: 'border-indigo-500/40',
      summary: 'Auto mode summary',
      whenToUse: 'When you want auto',
    },
    {
      id: 'resource-grounded',
      name: 'Grounded',
      icon: Shield,
      color: 'text-emerald-400',
      borderColor: 'border-emerald-500/40',
      summary: 'Grounded mode summary',
      whenToUse: 'When you want grounded',
    },
  ];

  it('renders model name, mode, subject, and action buttons', () => {
    render(
      <MemoryRouter>
        <ChatHeader
          activeProvider={{ model_name: 'gemini-2.5-flash', provider_type: 'gemini' }}
          providers={[{ id: 'p1', model_name: 'gemini-2.5-flash', is_default: true }]}
          selectedSubjectId=""
          subjects={[{ id: 'sub-1', name: 'Operating Systems' }]}
          onSelectSubject={vi.fn()}
          chatMode="auto"
          chatModes={mockModes}
          onSelectChatMode={vi.fn()}
          onOpenModeHelp={vi.fn()}
          onOpenSystemGuide={vi.fn()}
          onOpenAgyUsage={vi.fn()}
          onExportMarkdown={vi.fn()}
          canExport={true}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('gemini-2.5-flash')).toBeInTheDocument();
    expect(screen.getByText('All Subjects')).toBeInTheDocument();
    expect(screen.getByText('Auto')).toBeInTheDocument();
    expect(screen.getAllByText('AGY Quotas')[0]).toBeInTheDocument();
  });
});

describe('MessageComposer', () => {
  it('renders input, mode cycle button, web search toggle, and send button', () => {
    const handleSend = vi.fn();
    const handleToggleWeb = vi.fn();

    const mockModes: ChatModeDefinition[] = [
      {
        id: 'auto',
        name: 'Auto',
        icon: Sparkles,
        color: 'text-indigo-400',
        borderColor: 'border-indigo-500/40',
        summary: 'Auto',
        whenToUse: 'Auto',
      },
    ];

    render(
      <MessageComposer
        inputText="Explain binary search"
        onChangeText={vi.fn()}
        onSendMessage={handleSend}
        isStreaming={false}
        onStopStream={vi.fn()}
        chatMode="auto"
        chatModes={mockModes}
        onChangeChatMode={vi.fn()}
        webSearchEnabled={false}
        onToggleWebSearch={handleToggleWeb}
        onOpenSubjectPicker={vi.fn()}
        selectedSubjectName="Operating Systems"
      />
    );

    expect(screen.getByDisplayValue('Explain binary search')).toBeInTheDocument();
    expect(screen.getByText('Operating Systems')).toBeInTheDocument();
    expect(screen.getByText('Web Search')).toBeInTheDocument();

    const sendBtn = screen.getByTitle('Send message (Enter)');
    expect(sendBtn).toBeInTheDocument();
    fireEvent.click(sendBtn);
    expect(handleSend).toHaveBeenCalled();
  });
});
