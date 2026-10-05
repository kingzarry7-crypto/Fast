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
  className?: string;
}

export function ChatMessage({
  role,
  content,
  timestamp,
  status,
  isStreaming = false,
  isError = false,
  imagePreviewUrl,
  onCopy,
  onRegenerate,
  onSpeak,
  onSuggestion,
  className = "",
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState<"up" | "down" | null>(null);
  const [saved, setSaved] = useState(false);
  const [shared, setShared] = useState(false);

  const normalizedRole = role.toLowerCase();
  const isUser = normalizedRole === "user";
  const isSystem = normalizedRole === "system";

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

  if (isSystem) {
    return (
      <div className={"flex justify-center w-full my-2 " + className}>
        <div className="rounded-full border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-center text-[11px] font-mono uppercase tracking-widest text-zinc-400">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div
      className={
        "group flex w-full my-1 " +
        (isUser ? "justify-end" : "justify-start") +
        " " +
        className
      }
    >
      <div
        className={
          "relative max-w-[min(100%,36rem)] rounded-2xl px-4 py-3 text-sm leading-relaxed " +
          (isUser
            ? "bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-br-md shadow-[0_0_24px_rgba(0,0,0,0.18)]"
            : isError
              ? "bg-red-950/40 border border-red-500/30 text-red-100 rounded-bl-md"
              : "bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-bl-md")
        }
      >
        {imagePreviewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imagePreviewUrl}
            alt="attachment"
            className="mb-2 max-h-48 rounded-lg border border-zinc-700 object-cover"
          />
        ) : null}

        <div className="whitespace-pre-wrap break-words">{content}</div>

        {(timestamp || status || isStreaming) && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] tracking-wide text-zinc-500">
            {timestamp ? <span>{timestamp}</span> : null}
            {status ? <span>{status}</span> : null}
            {isStreaming ? <span className="animate-pulse">streaming…</span> : null}
          </div>
        )}

        {!isUser && !isError && content && !isStreaming ? (
          <>
            <div className="mt-3 flex flex-wrap items-center gap-0.5 border-t border-zinc-800/70 pt-2 opacity-75 transition-opacity group-hover:opacity-100">
              <button type="button" onClick={handleCopy} className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" title="Copy" aria-label="Copy">⧉</button>
              <button type="button" onClick={handleShare} className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" title="Share" aria-label="Share">↗</button>
              {onRegenerate ? <button type="button" onClick={onRegenerate} className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" title="Regenerate" aria-label="Regenerate">↻</button> : null}
              <button type="button" onClick={() => setLiked((v) => (v === "up" ? null : "up"))} className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" title="Like" aria-label="Like">♡</button>
              <button type="button" onClick={() => setLiked((v) => (v === "down" ? null : "down"))} className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" title="Dislike" aria-label="Dislike">♧</button>
              <button type="button" onClick={handleSave} className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" title="Save" aria-label="Save">▣</button>
              {onSpeak ? <button type="button" onClick={onSpeak} className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" title="Speak" aria-label="Speak">◉</button> : null}
              <button type="button" className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" title="More" aria-label="More">•••</button>
            </div>
            {onSuggestion ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {["Tell me more", "Give me an example", "What should I do next?"].map((suggestion) => (
                  <button key={suggestion} type="button" onClick={() => onSuggestion(suggestion)} className="rounded-full border border-cyan-500/20 bg-[#07111d] px-3 py-1.5 text-[11px] text-cyan-100/80 transition hover:border-cyan-400/40 hover:bg-cyan-400/10 hover:text-cyan-100">
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
