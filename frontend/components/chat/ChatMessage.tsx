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

        {!isUser && !isError && content ? (
          <div className="mt-2.5 flex flex-wrap items-center gap-1 opacity-70 transition-opacity group-hover:opacity-100">
            <button type="button" onClick={handleCopy} className="rounded-md border border-zinc-700 px-2 py-1 text-[10px] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" title="Copy">{copied ? "Copied" : "Copy"}</button>
            <button type="button" onClick={() => setLiked((v) => (v === "up" ? null : "up"))} className={"rounded-md border px-2 py-1 text-[10px] " + (liked === "up" ? "border-zinc-500 text-zinc-200 bg-zinc-800" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800")} title="Like">Like</button>
            <button type="button" onClick={() => setLiked((v) => (v === "down" ? null : "down"))} className={"rounded-md border px-2 py-1 text-[10px] " + (liked === "down" ? "border-zinc-500 text-zinc-200 bg-zinc-800" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800")} title="Dislike">Dislike</button>
            <button type="button" onClick={handleShare} className="rounded-md border border-zinc-700 px-2 py-1 text-[10px] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" title="Share">{shared ? "Shared" : "Share"}</button>
            <button type="button" onClick={handleSave} className={"rounded-md border px-2 py-1 text-[10px] " + (saved ? "border-zinc-500 text-zinc-200 bg-zinc-800" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800")} title="Save">{saved ? "Saved" : "Save"}</button>
            {onSpeak ? (
              <button type="button" onClick={onSpeak} className="rounded-md border border-zinc-700 px-2 py-1 text-[10px] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" title="Speak">Speak</button>
            ) : null}
            {onRegenerate ? (
              <button type="button" onClick={onRegenerate} className="rounded-md border border-zinc-700 px-2 py-1 text-[10px] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" title="Regenerate">Retry</button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}


export default ChatMessage;
