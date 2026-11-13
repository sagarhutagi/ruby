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
    <div className="space-y-3 text-xs leading-relaxed text-zinc-200">
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
    <div className="rounded-lg bg-zinc-950 border border-zinc-800 overflow-hidden my-2">
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-900 border-b border-zinc-800 text-[11px] font-mono text-zinc-400">
        <span>{lang}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3 font-mono text-[11px] overflow-x-auto text-zinc-300 leading-normal">
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
        <h4 key={i} className="text-xs font-semibold text-zinc-100 mt-3 mb-1">
          {renderInline(trimmed.slice(4), onCitationClick)}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={i} className="text-sm font-semibold text-zinc-100 mt-4 mb-1.5 border-b border-zinc-800 pb-1">
          {renderInline(trimmed.slice(3), onCitationClick)}
        </h3>
      );
    } else if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={i} className="text-base font-bold text-zinc-100 mt-4 mb-2">
          {renderInline(trimmed.slice(2), onCitationClick)}
        </h2>
      );
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <li key={i} className="ml-4 list-disc text-zinc-300 my-0.5">
          {renderInline(trimmed.slice(2), onCitationClick)}
        </li>
      );
    } else if (/^\d+\.\s+/.test(trimmed)) {
      const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
      elements.push(
        <li key={i} className="ml-4 list-decimal text-zinc-300 my-0.5">
          {renderInline(numMatch ? numMatch[2] : trimmed, onCitationClick)}
        </li>
      );
    } else if (trimmed.startsWith('> ')) {
      elements.push(
        <blockquote key={i} className="border-l-2 border-indigo-500 pl-3 my-2 text-zinc-400 italic">
          {renderInline(trimmed.slice(2), onCitationClick)}
        </blockquote>
      );
    } else if (trimmed === '---') {
      elements.push(<hr key={i} className="border-zinc-800 my-3" />);
    } else if (trimmed === '') {
      elements.push(<div key={i} className="h-1.5" />);
    } else {
      elements.push(
        <p key={i} className="my-1 text-zinc-300 leading-relaxed">
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
  // skip rows[1] if it's separator |---|---|
  const dataRows = rows.slice(rows[1].includes('---') ? 2 : 1).map(parseRow);

  return (
    <div className="overflow-x-auto my-3 rounded-lg border border-zinc-800">
      <table className="w-full text-left border-collapse text-[11px]">
        <thead>
          <tr className="bg-zinc-900 border-b border-zinc-800">
            {headers.map((h, i) => (
              <th key={i} className="p-2 font-semibold text-zinc-200">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/60 bg-zinc-950/40">
          {dataRows.map((r, ri) => (
            <tr key={ri} className="hover:bg-zinc-900/40 transition-colors">
              {r.map((c, ci) => (
                <td key={ci} className="p-2 text-zinc-300">
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
  // Regex splitting by:
  // 1. Inline KaTeX math: $...$
  // 2. Citation markers: [Doc: ...] or [SOURCE #X]
  // 3. Bold text: **...**
  // 4. Inline code: `...`
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
            className="inline-block px-1 mx-0.5 rounded bg-zinc-900/60 font-sans"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        );
      } catch {
        return <code key={idx} className="font-mono text-zinc-400">{part}</code>;
      }
    }

    // Citation badge
    if (
      (part.startsWith('[Doc:') || part.startsWith('[Document:') || part.startsWith('[SOURCE')) &&
      part.endsWith(']')
    ) {
      return (
        <button
          key={idx}
          onClick={() => onCitationClick && onCitationClick(part)}
          className="inline-flex items-center gap-1 mx-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/70 border border-indigo-700/60 text-indigo-300 hover:bg-indigo-900 hover:text-indigo-100 transition-colors cursor-pointer"
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
        <strong key={idx} className="font-semibold text-zinc-100">
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Inline code
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code key={idx} className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-200 font-mono text-[11px]">
          {part.slice(1, -1)}
        </code>
      );
    }

    return <span key={idx}>{part}</span>;
  });
}
