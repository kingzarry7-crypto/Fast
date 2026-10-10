"use client";

import React, { useState } from "react";

export interface ChatMessageProps {
  id?: string;
  role: "user" | "assistant" | "system" | string;
  content: string;
  timestamp?: string;
  model?: string;
  status?: string;
  isStreaming?: boolean;
  isError?: boolean;
  imagePreviewUrl?: string;
  onCopy?: (content: string) => void;
  onRegenerate?: () => void;
  onSpeak?: () => void;
  onSuggestion?: (text: string) => void;
  suggestions?: string[];
  className?: string;
}

export function ChatMessage({
  role,
  content,
  timestamp,
  isStreaming = false,
  isError = false,
  imagePreviewUrl,
  onCopy,
  onRegenerate,
  onSpeak,
  onSuggestion,
  suggestions = [],
  className = "",
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState<"up" | "down" | null>(null);
  const [saved, setSaved] = useState(false);
  const [shared, setShared] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [suggestionsOpen, setSuggestionsOpen] = useState(true);

  const normalizedRole = role.toLowerCase();
  const isUser = normalizedRole === "user";
  const isSystem = normalizedRole === "system";

  // Chat is rendered as plain text, so never expose Markdown emphasis markers.
  const displayContent = content.replaceAll("***", "").replaceAll("**", "").replaceAll("__", "");

  const handleCopy = async () => {
    try {
      if (onCopy) onCopy(content);
      else await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const handleShare = async () => {
    try {
      if (navigator.share) {
        await navigator.share({ text: content, title: "King Zarry AI" });
      } else {
        await navigator.clipboard.writeText(content);
      }
      setShared(true);
      setTimeout(() => setShared(false), 2000);
    } catch {
      /* cancelled */
    }
  };

  const handleSave = () => {
    setSaved((v) => !v);
    try {
      const key = "kz_saved_messages";
      const raw = localStorage.getItem(key);
      const list: string[] = raw ? JSON.parse(raw) : [];
      if (!saved) {
        list.unshift(content.slice(0, 4000));
        localStorage.setItem(key, JSON.stringify(list.slice(0, 50)));
      }
    } catch {
      /* ignore */
    }
  };

  const handleDownload = () => {
    try {
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "king-zarry-ai-response.txt";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setMoreOpen(false);
    } catch {
      /* ignore */
    }
  };

  const handleMoreSuggestions = () => {
    setSuggestionsOpen(true);
    setMoreOpen(false);
  };



  if (isSystem) {
    return (
      <div className={"flex justify-center w-full my-2 " + className}>
        <div className="rounded-full border border-cyan-500/20 bg-[#031322]/80 px-3 py-1.5 text-center text-[11px] font-mono uppercase tracking-widest text-cyan-100/55">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div
      className={
        "group flex w-full my-2 " +
        (isUser ? "justify-end" : "justify-start") +
        " " +
        className
      }
    >
      <div
        className={
          "relative w-fit max-w-[min(88%,820px)] px-4 py-3 sm:px-5 sm:py-4 text-[14px] leading-7 " +
          (isUser
            ? "ml-auto rounded-2xl rounded-br-md border border-cyan-300/20 bg-gradient-to-br from-cyan-300/[0.12] via-blue-400/[0.07] to-amber-300/[0.035] text-slate-50 shadow-[0_12px_35px_rgba(0,0,0,0.14)]"
            : "mr-auto rounded-2xl border border-white/[0.035] bg-white/[0.012] text-[#d9eaf4]") +
          " " +
          (isError ? "text-red-100" : "")
        }
      >
        <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-100/50">
          <span>{isUser ? "You" : "King Zarry AI"}</span>
        </div>
        {imagePreviewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imagePreviewUrl}
            alt="attachment"
            className="mb-2 max-h-48 rounded-lg object-cover"
          />
        ) : null}

        <div className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{displayContent}{isStreaming ? <span aria-hidden="true" className="ml-0.5 inline-block h-[1em] w-[2px] translate-y-[2px] animate-pulse rounded-full bg-cyan-300 align-baseline" /> : null}</div>

        {timestamp ? <div className="mt-2 text-[10px] tracking-wide text-cyan-100/35">{timestamp}</div> : null}

        {!isUser && !isError && content && !isStreaming ? (
          <>
            <div className="mt-3 flex flex-wrap items-center gap-0.5 pt-1 opacity-75 transition-opacity group-hover:opacity-100">
              <button type="button" onClick={handleCopy} className="flex h-8 w-8 items-center justify-center rounded-md text-cyan-100/45 hover:bg-transparent hover:text-cyan-100" title="Copy" aria-label="Copy">⧉</button>
              <button type="button" onClick={handleShare} className="flex h-8 w-8 items-center justify-center rounded-md text-cyan-100/45 hover:bg-cyan-400/10 hover:text-cyan-100" title="Share" aria-label="Share">↗</button>
              {onRegenerate ? <button type="button" onClick={onRegenerate} className="flex h-8 w-8 items-center justify-center rounded-md text-cyan-100/45 hover:bg-cyan-400/10 hover:text-cyan-100" title="Regenerate" aria-label="Regenerate">↻</button> : null}
              <button type="button" onClick={() => setLiked((v) => (v === "up" ? null : "up"))} className="flex h-8 w-8 items-center justify-center rounded-md text-cyan-100/45 hover:bg-cyan-400/10 hover:text-cyan-100" title="Like" aria-label="Like">♡</button>
              <button type="button" onClick={() => setLiked((v) => (v === "down" ? null : "down"))} className="flex h-8 w-8 items-center justify-center rounded-md text-cyan-100/45 hover:bg-cyan-400/10 hover:text-cyan-100" title="Dislike" aria-label="Dislike">♧</button>
              <button type="button" onClick={handleSave} className="flex h-8 w-8 items-center justify-center rounded-md text-cyan-100/45 hover:bg-cyan-400/10 hover:text-cyan-100" title="Save" aria-label="Save">▣</button>
              {onSpeak ? <button type="button" onClick={onSpeak} className="flex h-8 w-8 items-center justify-center rounded-md text-cyan-100/45 hover:bg-cyan-400/10 hover:text-cyan-100" title="Speak" aria-label="Speak">◉</button> : null}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setMoreOpen((v) => !v)}
                  className={"flex h-8 w-8 items-center justify-center rounded-md text-cyan-100/45 hover:bg-cyan-400/10 hover:text-cyan-100 " + (moreOpen ? "bg-cyan-400/10 text-cyan-100" : "")}
                  title="More actions"
                  aria-label="More actions"
                  aria-expanded={moreOpen}
                >
                  •••
                </button>
                {moreOpen ? (
                  <div className="absolute bottom-10 right-0 z-50 w-52 overflow-hidden rounded-xl border border-cyan-500/20 bg-[#06101a]/98 p-1.5 shadow-2xl backdrop-blur-xl">
                    <button type="button" onClick={() => { void handleCopy(); setMoreOpen(false); }} className="flex w-full items-center rounded-lg px-3 py-2 text-left text-xs text-cyan-100/75 hover:bg-cyan-400/10 hover:text-cyan-50">⧉ <span className="ml-2">Copy response</span></button>
                    <button type="button" onClick={() => { void handleShare(); setMoreOpen(false); }} className="flex w-full items-center rounded-lg px-3 py-2 text-left text-xs text-cyan-100/75 hover:bg-cyan-400/10 hover:text-cyan-50">↗ <span className="ml-2">Share response</span></button>
                    {onRegenerate ? <button type="button" onClick={() => { setMoreOpen(false); onRegenerate(); }} className="flex w-full items-center rounded-lg px-3 py-2 text-left text-xs text-cyan-100/75 hover:bg-cyan-400/10 hover:text-cyan-50">↻ <span className="ml-2">Regenerate response</span></button> : null}
                    <button type="button" onClick={() => { handleSave(); setMoreOpen(false); }} className="flex w-full items-center rounded-lg px-3 py-2 text-left text-xs text-cyan-100/75 hover:bg-cyan-400/10 hover:text-cyan-50">▣ <span className="ml-2">{saved ? "Remove from saved" : "Save response"}</span></button>
                    {onSpeak ? <button type="button" onClick={() => { setMoreOpen(false); onSpeak(); }} className="flex w-full items-center rounded-lg px-3 py-2 text-left text-xs text-cyan-100/75 hover:bg-cyan-400/10 hover:text-cyan-50">◉ <span className="ml-2">Speak response</span></button> : null}
                    <button type="button" onClick={handleDownload} className="flex w-full items-center rounded-lg px-3 py-2 text-left text-xs text-cyan-100/75 hover:bg-cyan-400/10 hover:text-cyan-50">↓ <span className="ml-2">Download as TXT</span></button>
                    {onSuggestion && suggestions.length ? <button type="button" onClick={handleMoreSuggestions} className="flex w-full items-center rounded-lg px-3 py-2 text-left text-xs text-cyan-100/75 hover:bg-cyan-400/10 hover:text-cyan-50">✦ <span className="ml-2">Show follow-up options</span></button> : null}
                  </div>
                ) : null}
              </div>
            </div>
            {onSuggestion && suggestionsOpen && suggestions.length ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {suggestions.map((suggestion) => (
                  <button key={suggestion} type="button" onClick={() => onSuggestion(suggestion)} className="rounded-full border border-cyan-500/25 bg-[#031322]/70 px-3 py-1.5 text-[11px] text-cyan-100/80 transition hover:border-cyan-400/40 hover:bg-cyan-400/10 hover:text-cyan-100">
                    {suggestion}
                  </button>
                ))}
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}


export default ChatMessage;
