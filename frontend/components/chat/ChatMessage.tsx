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
      /* user cancelled */
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
      <div className={`flex justify-center w-full my-3 ${className}`}>
        <div className="px-4 py-2 text-center text-[11px] font-mono tracking-widest uppercase text-zinc-400 bg-zinc-900/60 border border-zinc-700/50 rounded-full">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`group flex w-full my-1 ${
        isUser ? "justify-end" : "justify-start"
      } ${className}`}
    >
      <div
        className={`relative max-w-[min(100%,42rem)] w-full ${
          isUser ? "pl-8" : "pr-4"
        }`}
      >
        <div
          className={`mb-1.5 flex items-center gap-2 text-[11px] font-medium ${
            isUser ? "justify-end text-zinc-500" : "text-zinc-400"
          }`}
        >
          {!isUser && (
            <span className="inline-flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center text-[9px] font-bold text-black">
                KZ
              </span>
              <span className="text-zinc-300">King Zarry AI</span>
            </span>
          )}
          {isUser && <span className="text-zinc-500">You</span>}
          {timestamp && (
            <span className="text-zinc-600 font-mono text-[10px]">{timestamp}</span>
          )}
        </div>

        <div
          className={`rounded-2xl px-4 py-3 text-[15px] leading-relaxed whitespace-pre-wrap break-words ${
            isUser
              ? "bg-zinc-800 text-zinc-100 rounded-br-md"
              : isError
                ? "bg-red-950/40 border border-red-500/30 text-red-100"
                : "bg-transparent text-zinc-100"
          }`}
        >
          {imagePreviewUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imagePreviewUrl}
              alt="attachment"
              className="mb-3 max-h-48 rounded-xl border border-zinc-700 object-cover"
            />
          )}
          {content}
          {isStreaming && (
            <span
              className="inline-block w-2 h-4 ml-1 bg-zinc-300 animate-pulse align-middle rounded-sm"
              aria-hidden
            />
          )}
        </div>

        {!isUser && !isStreaming && content && (
          <div className="mt-2 flex flex-wrap items-center gap-0.5 opacity-80 group-hover:opacity-100 transition-opacity">
            <ActionBtn
              title="Copy"
              active={copied}
              onClick={handleCopy}
              label={copied ? "Copied" : undefined}
            >
              {copied ? <CheckIcon /> : <CopyIcon />}
            </ActionBtn>

            <ActionBtn
              title="Like"
              active={liked === "up"}
              onClick={() => setLiked((v) => (v === "up" ? null : "up"))}
            >
              <ThumbUpIcon filled={liked === "up"} />
            </ActionBtn>

            <ActionBtn
              title="Dislike"
              active={liked === "down"}
              onClick={() => setLiked((v) => (v === "down" ? null : "down"))}
            >
              <ThumbDownIcon filled={liked === "down"} />
            </ActionBtn>

            <ActionBtn
              title="Share"
              active={shared}
              onClick={handleShare}
              label={shared ? "Shared" : undefined}
            >
              <ShareIcon />
            </ActionBtn>

            <ActionBtn
              title="Save"
              active={saved}
              onClick={handleSave}
              label={saved ? "Saved" : undefined}
            >
              <BookmarkIcon filled={saved} />
            </ActionBtn>

            {onSpeak && (
              <ActionBtn title="Speak" onClick={onSpeak}>
                <SpeakerIcon />
              </ActionBtn>
            )}

            {onRegenerate && (
              <ActionBtn title="Regenerate" onClick={onRegenerate}>
                <RefreshIcon />
              </ActionBtn>
            )}

            {status && (
              <span className="ml-2 text-[10px] font-mono text-zinc-600 tracking-wide">
                {status}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ActionBtn({
  children,
  title,
  onClick,
  active,
  label,
}: {
  children: React.ReactNode;
  title: string;
  onClick?: () => void;
  active?: boolean;
  label?: string;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs transition-colors ${
        active
          ? "text-cyan-300 bg-cyan-500/10"
          : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/80"
      }`}
    >
      {children}
      {label && <span className="text-[10px]">{label}</span>}
    </button>
  );
}

function CopyIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

function ThumbUpIcon({ filled }: { filled?: boolean }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.75">
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
    </svg>
  );
}

function ThumbDownIcon({ filled }: { filled?: boolean }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.75">
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10zM17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
    </svg>
  );
}

function ShareIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
    </svg>
  );
}

function BookmarkIcon({ filled }: { filled?: boolean }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.75">
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function SpeakerIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M23 4v6h-6M1 20v-6h6" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

export function ThinkingIndicator({
  phase = "thinking",
}: {
  phase?: "reading" | "thinking" | "searching" | "responding";
}) {
  const labels: Record<string, string> = {
    reading: "Reading",
    thinking: "Thinking",
    searching: "Searching",
    responding: "Responding",
  };

  return (
    <div className="flex items-start gap-3 py-2 px-1">
      <span className="w-5 h-5 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center text-[9px] font-bold text-black shrink-0 mt-0.5">
        KZ
      </span>
      <div className="flex flex-col gap-1.5 pt-0.5">
        <div className="flex items-center gap-2 text-sm text-zinc-400">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400" />
          </span>
          <span className="font-medium text-zinc-300">
            {labels[phase] || "Thinking"}
          </span>
          <span className="inline-flex gap-0.5 ml-0.5">
            <span className="w-1 h-1 rounded-full bg-zinc-500 animate-bounce [animation-delay:0ms]" />
            <span className="w-1 h-1 rounded-full bg-zinc-500 animate-bounce [animation-delay:150ms]" />
            <span className="w-1 h-1 rounded-full bg-zinc-500 animate-bounce [animation-delay:300ms]" />
          </span>
        </div>
        <div className="h-1 w-32 rounded-full bg-zinc-800 overflow-hidden">
          <div className="h-full w-1/2 rounded-full bg-gradient-to-r from-cyan-500/80 to-blue-500/80 animate-pulse" />
        </div>
      </div>
    </div>
  );
}

export default ChatMessage;
