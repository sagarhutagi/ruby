import React, { useState } from 'react';
import { Globe, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';

export interface WebSource {
  title: string;
  url: string;
  snippet?: string;
  published_date?: string;
}

interface WebSourceCardProps {
  source: WebSource;
  index: number;
}

export const WebSourceCard: React.FC<WebSourceCardProps> = ({ source, index }) => {
  // Extract hostname for clean domain badge
  let hostname = '';
  try {
    hostname = new URL(source.url).hostname.replace(/^www\./, '');
  } catch {
    hostname = source.url.split('/')[2] || 'web';
  }

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group relative flex flex-col justify-between p-3 rounded-xl bg-[#242424] hover:bg-[#2a2a2a] border border-[#333333] hover:border-[#4d4d4d] transition-all duration-150 cursor-pointer shadow-sm text-left"
    >
      <div>
        {/* Header: Domain Badge and Index */}
        <div className="flex items-center justify-between gap-1.5 mb-1.5">
          <div className="flex items-center gap-1.5 min-w-0">
            <div className="w-4 h-4 rounded-full bg-sky-950/80 border border-sky-800/60 flex items-center justify-center shrink-0">
              <Globe className="w-2.5 h-2.5 text-sky-400" />
            </div>
            <span className="text-[11px] font-mono text-[#a1a1aa] truncate group-hover:text-sky-300">
              {hostname}
            </span>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#1c1c1c] text-[#71717a] border border-[#303030]">
              #{index + 1}
            </span>
            <ExternalLink className="w-3 h-3 text-[#71717a] group-hover:text-white transition-colors" />
          </div>
        </div>

        {/* Title */}
        <h4 className="text-xs font-medium text-[#ececec] group-hover:text-white line-clamp-1 leading-snug">
          {source.title}
        </h4>

        {/* Snippet */}
        {source.snippet && (
          <p className="text-[11px] text-[#9ca3af] leading-relaxed line-clamp-2 mt-1">
            {source.snippet}
          </p>
        )}
      </div>

      {/* Footer publication info if available */}
      {source.published_date && (
        <div className="mt-2 text-[10px] text-[#6b7280] font-mono">
          {source.published_date}
        </div>
      )}
    </a>
  );
};

interface WebSourceGridProps {
  sources: WebSource[];
  defaultExpanded?: boolean;
}

export const WebSourceGrid: React.FC<WebSourceGridProps> = ({ sources, defaultExpanded = false }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (!sources || sources.length === 0) return null;

  const visibleSources = expanded ? sources : sources.slice(0, 4);
  const hasMore = sources.length > 4;

  return (
    <div className="mt-3.5 pt-3 border-t border-[#2e2e2e]">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-sky-950/70 border border-sky-800/60 flex items-center justify-center">
            <Globe className="w-3 h-3 text-sky-400" />
          </div>
          <span className="text-xs font-medium text-[#e4e4e7]">
            Web Sources <span className="text-[#a1a1aa] font-mono">({sources.length})</span>
          </span>
        </div>

        {hasMore && (
          <button
            onClick={() => setExpanded((prev) => !prev)}
            className="flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 font-medium px-2 py-0.5 rounded hover:bg-[#282828] transition-colors cursor-pointer"
          >
            <span>{expanded ? 'Show fewer' : `+${sources.length - 4} more`}</span>
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {visibleSources.map((src, idx) => (
          <WebSourceCard key={idx} source={src} index={idx} />
        ))}
      </div>
    </div>
  );
};
