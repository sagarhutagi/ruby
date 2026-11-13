import React, { useState } from 'react';
import katex from 'katex';
import { Copy, Check, ExternalLink } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  onCitationClick?: (citationTag: string) => void;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, onCitationClick }) => {
  // Split content by code blocks first
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-4 text-[15px] leading-7 text-[#ececec] font-sans">
      {parts.map((part, idx) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          return <CodeBlock key={idx} codeBlock={part} />;
        }
        return <TextBlock key={idx} text={part} onCitationClick={onCitationClick} />;
      })}
    </div>
  );
};

const CodeBlock: React.FC<{ codeBlock: string }> = ({ codeBlock }) => {
  const [copied, setCopied] = useState(false);

  // Extract language and code
  const firstNewline = codeBlock.indexOf('\n');
  const lang = codeBlock.slice(3, firstNewline).trim() || 'code';
  const code = codeBlock.slice(firstNewline + 1, -3);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl bg-[#0d0d0d] border border-[#2f2f2f] overflow-hidden my-3 shadow-md">
      <div className="flex items-center justify-between px-4 py-2 bg-[#1e1e1e] border-b border-[#2f2f2f] text-xs font-mono text-[#b4b4b4]">
        <span className="font-medium lowercase">{lang}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-[#b4b4b4] hover:text-white transition-colors cursor-pointer py-0.5 px-2 rounded hover:bg-[#2f2f2f]"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-sans">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span className="font-sans">Copy code</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-4 font-mono text-[13px] overflow-x-auto text-[#f1f1f1] leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
};

const TextBlock: React.FC<{ text: string; onCitationClick?: (tag: string) => void }> = ({
  text,
  onCitationClick,
}) => {
  // Split text by lines
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];

  let inTable = false;
  let tableRows: string[] = [];

  const flushTable = (keyPrefix: number) => {
    if (tableRows.length > 0) {
      elements.push(<MarkdownTable key={`table-${keyPrefix}`} rows={tableRows} />);
      tableRows = [];
    }
    inTable = false;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Check table
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|')) {
      inTable = true;
      tableRows.push(trimmed);
      continue;
    } else if (inTable) {
      flushTable(i);
    }

    // Block LaTeX math: $$ ... $$
    if (trimmed.startsWith('$$') && trimmed.endsWith('$$') && trimmed.length > 4) {
      const math = trimmed.slice(2, -2).trim();
      try {
        const html = katex.renderToString(math, { displayMode: true, throwOnError: false });
        elements.push(
          <div
            key={i}
            className="my-3 p-2 bg-zinc-950/60 rounded border border-zinc-850 overflow-x-auto text-center"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        );
      } catch {
        elements.push(<div key={i} className="font-mono text-xs my-2">{trimmed}</div>);
      }
      continue;
    }

    // Headings
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={i} className="text-base font-semibold text-[#f4f4f5] mt-4 mb-1">
          {renderInline(trimmed.slice(4), onCitationClick)}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={i} className="text-lg font-semibold text-[#f4f4f5] mt-5 mb-2 border-b border-[#333] pb-1">
          {renderInline(trimmed.slice(3), onCitationClick)}
        </h3>
      );
    } else if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={i} className="text-xl font-bold text-white mt-6 mb-2.5">
          {renderInline(trimmed.slice(2), onCitationClick)}
        </h2>
      );
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <li key={i} className="ml-5 list-disc text-[#d1d5db] my-1 marker:text-[#888]">
          {renderInline(trimmed.slice(2), onCitationClick)}
        </li>
      );
    } else if (/^\d+\.\s+/.test(trimmed)) {
      const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
      elements.push(
        <li key={i} className="ml-5 list-decimal text-[#d1d5db] my-1 marker:text-[#888]">
          {renderInline(numMatch ? numMatch[2] : trimmed, onCitationClick)}
        </li>
      );
    } else if (trimmed.startsWith('> ')) {
      elements.push(
        <blockquote key={i} className="border-l-2 border-[#555] pl-3.5 my-2.5 text-[#a1a1aa] italic">
          {renderInline(trimmed.slice(2), onCitationClick)}
        </blockquote>
      );
    } else if (trimmed === '---') {
      elements.push(<hr key={i} className="border-[#383838] my-4" />);
    } else if (trimmed === '') {
      elements.push(<div key={i} className="h-2" />);
    } else {
      elements.push(
        <p key={i} className="my-1 text-[#ececec] leading-relaxed">
          {renderInline(line, onCitationClick)}
        </p>
      );
    }
  }

  flushTable(lines.length);

  return <>{elements}</>;
};

const MarkdownTable: React.FC<{ rows: string[] }> = ({ rows }) => {
  if (rows.length < 2) return null;

  const parseRow = (r: string) =>
    r
      .split('|')
      .slice(1, -1)
      .map((c) => c.trim());

  const headers = parseRow(rows[0]);
  const dataRows = rows.slice(rows[1].includes('---') ? 2 : 1).map(parseRow);

  return (
    <div className="overflow-x-auto my-3 rounded-xl border border-[#383838] bg-[#1a1a1a]">
      <table className="w-full text-left border-collapse text-[13px]">
        <thead>
          <tr className="bg-[#242424] border-b border-[#383838]">
            {headers.map((h, i) => (
              <th key={i} className="px-3.5 py-2 font-medium text-[#ececec]">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#2d2d2d]">
          {dataRows.map((r, ri) => (
            <tr key={ri} className="hover:bg-[#222222] transition-colors">
              {r.map((c, ci) => (
                <td key={ci} className="px-3.5 py-2 text-[#d4d4d8]">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

function renderInline(text: string, onCitationClick?: (tag: string) => void): React.ReactNode[] {
  const tokenRegex = /(\$[^$\n]+\$|\[(?:Doc|Document):[^\]]+\]|\[SOURCE\s*#?\d+\]|\*\*[^*]+\*\*|`[^`]+`)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, idx) => {
    if (!part) return null;

    // Inline KaTeX Math
    if (part.startsWith('$') && part.endsWith('$') && part.length > 2) {
      const math = part.slice(1, -1);
      try {
        const html = katex.renderToString(math, { displayMode: false, throwOnError: false });
        return (
          <span
            key={idx}
            className="inline-block px-1.5 py-0.5 mx-0.5 rounded bg-[#2a2a2a] border border-[#3a3a3a] font-sans"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        );
      } catch {
        return <code key={idx} className="font-mono text-[#a1a1aa]">{part}</code>;
      }
    }

    // Citation badge - styled as sleek pill
    if (
      (part.startsWith('[Doc:') || part.startsWith('[Document:') || part.startsWith('[SOURCE')) &&
      part.endsWith(']')
    ) {
      return (
        <button
          key={idx}
          onClick={() => onCitationClick && onCitationClick(part)}
          className="inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded-full text-xs font-mono bg-[#2a2b32] border border-[#3e404b] text-[#93c5fd] hover:bg-[#343642] hover:text-white transition-colors cursor-pointer shadow-sm"
          title="Click to inspect source citation"
        >
          <span>{part}</span>
          <ExternalLink className="w-2.5 h-2.5 opacity-70" />
        </button>
      );
    }

    // Bold text
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={idx} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Inline code
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code key={idx} className="px-1.5 py-0.5 rounded bg-[#2a2a2a] text-[#f4f4f5] border border-[#383838] font-mono text-[13px]">
          {part.slice(1, -1)}
        </code>
      );
    }

    return <span key={idx}>{part}</span>;
  });
}
