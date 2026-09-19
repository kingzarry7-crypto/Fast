import React from "react";

export interface NewsCardProps {
  title?: string;
  headline?: string;
  description?: string;
  summary?: string;
  source?: string;
  author?: string;
  category?: string;
  publishedAt?: string;
  timestamp?: string;
  image?: string;
  url?: string;
  tags?: string[];
  sentiment?: string;
  relevance?: string;
  marketImpact?: string;
  aiSummary?: string;
  readingTime?: string;
  onClick?: () => void;
  className?: string;
}

export function NewsCard({
  title,
  headline,
  description,
  summary,
  source,
  author,
  category,
  publishedAt,
  timestamp,
  image,
  url,
  tags,
  sentiment,
  relevance,
  marketImpact,
  aiSummary,
  readingTime,
  onClick,
  className = "",
}: NewsCardProps) {
  const displayTitle = title || headline || "Untitled Intelligence Briefing";
  const displaySummary = summary || description;
  const displayTime = timestamp || publishedAt;
  const displaySource = source || author;

  const CardWrapper = url ? "a" : "div";
  const wrapperProps = url
    ? { href: url, target: "_blank", rel: "noopener noreferrer" }
    : onClick
    ? { role: "button", tabIndex: 0, onClick }
    : {};

  return (
    <CardWrapper
      {...wrapperProps}
      className={`group relative flex flex-col bg-black/85 backdrop-blur-2xl border border-cyan-500/25 hover:border-cyan-400 rounded-xl overflow-hidden shadow-[0_4px_25px_rgba(6,182,212,0.08)] hover:shadow-[0_0_30px_rgba(6,182,212,0.2)] transition-all duration-300 text-left cursor-pointer ${className}`}
    >
      {/* HUD corner brackets & scanline accents */}
      <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-cyan-400/50 pointer-events-none" aria-hidden="true" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-cyan-400/50 pointer-events-none" aria-hidden="true" />
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_98%,rgba(6,182,212,0.02)_100%)] bg-[size:100%_4px] pointer-events-none" aria-hidden="true" />

      {/* Top Source / Metadata Banner */}
      <div className="px-4 py-3 border-b border-cyan-500/15 flex items-center justify-between text-[10px] font-mono bg-gradient-to-r from-cyan-950/30 via-transparent to-transparent">
        <div className="flex items-center gap-2 truncate">
          {displaySource && (
            <span className="text-cyan-300 font-bold tracking-widest uppercase truncate flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.9)]" aria-hidden="true" />
              {displaySource}
            </span>
          )}
          {category && (
            <>
              <span className="text-cyan-500/40" aria-hidden="true">/</span>
              <span className="text-cyan-400/70 uppercase px-2 py-0.5 bg-cyan-950/60 border border-cyan-500/25 rounded tracking-wider">
                {category}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2 text-cyan-400/60 shrink-0">
          {readingTime && <span>{readingTime}</span>}
          {displayTime && (
            <>
              {readingTime && <span aria-hidden="true">•</span>}
              <span className="uppercase tracking-wider">{displayTime}</span>
            </>
          )}
        </div>
      </div>

      {/* Cinematic Image Frame */}
      {image && (
        <div className="relative w-full h-48 sm:h-52 overflow-hidden bg-cyan-950/20 border-b border-cyan-500/15">
          <img
            src={image}
            alt={displayTitle}
            className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500 opacity-90 group-hover:opacity-100"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent pointer-events-none" aria-hidden="true" />
          
          {/* Holographic overlay accent on image */}
          <div className="absolute top-2 left-2 px-2 py-0.5 bg-black/70 backdrop-blur-md border border-cyan-500/30 rounded text-[9px] font-mono text-cyan-300 tracking-widest uppercase flex items-center gap-1">
            <span className="w-1 h-1 rounded-full bg-cyan-400 animate-pulse" aria-hidden="true" />
            SECURE BRIEF
          </div>
        </div>
      )}

      {/* Main Content Body */}
      <div className="p-4 sm:p-5 flex flex-col flex-1 space-y-3">
        {/* Headline */}
        <h3 className="text-base sm:text-lg font-bold font-mono text-white group-hover:text-cyan-200 transition-colors tracking-wide leading-snug">
          {displayTitle}
        </h3>

        {/* Summary Description */}
        {displaySummary && (
          <p className="text-xs sm:text-sm font-sans text-cyan-100/75 line-clamp-3 leading-relaxed">
            {displaySummary}
          </p>
        )}

        {/* AI Intelligence Context Section (rendered ONLY if real data exists) */}
        {(aiSummary || sentiment || relevance || marketImpact) && (
          <div className="mt-2 pt-3 border-t border-cyan-500/20 bg-cyan-950/20 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
              <span className="flex items-center gap-1.5 font-bold">
                <svg className="w-3.5 h-3.5 text-cyan-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                AI INTELLIGENCE CONTEXT
              </span>
              <div className="flex items-center gap-2">
                {relevance && <span className="text-cyan-300 bg-cyan-900/60 px-1.5 py-0.5 rounded text-[9px]">REL: {relevance}</span>}
                {sentiment && <span className="text-cyan-300 bg-cyan-900/60 px-1.5 py-0.5 rounded text-[9px]">SENT: {sentiment}</span>}
              </div>
            </div>

            {aiSummary && (
              <p className="text-xs font-mono text-cyan-200/90 leading-relaxed">
                {aiSummary}
              </p>
            )}

            {marketImpact && (
              <div className="text-[10px] font-mono text-cyan-400/80">
                <span className="text-cyan-500 uppercase">Impact Focus:</span> {marketImpact}
              </div>
            )}
          </div>
        )}

        {/* Tags */}
        {tags && tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {tags.map((tag, idx) => (
              <span
                key={idx}
                className="text-[9px] font-mono bg-cyan-950/50 border border-cyan-500/25 text-cyan-300/80 px-2 py-0.5 rounded"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Card Footer Action */}
      <div className="px-4 py-3 border-t border-cyan-500/15 bg-black/60 flex items-center justify-between text-[11px] font-mono">
        <span className="text-cyan-400/50 uppercase tracking-wider text-[10px]">
          KING ZARRY INTELLIGENCE DECK
        </span>
        <span className="text-cyan-300 group-hover:text-white flex items-center gap-1 font-bold tracking-wider uppercase transition-colors">
          <span>READ BRIEF</span>
          <svg className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </span>
      </div>
    </CardWrapper>
  );
}
