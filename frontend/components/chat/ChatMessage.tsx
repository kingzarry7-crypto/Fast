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
      <div className={"flex justify-center w-full my-2 " + className}>
        <div className="px-3 py-1.5 text-center text-[10px] font-mono tracking-widest uppercase text-zinc-400 bg-zinc-800 border border-zinc-700 rounded-full">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div
      className={
        "group flex w-full my-0.5 " +
        (isUser ? "justify-end" : "justify-start") +
        " " +
        className
      }
    >
      <div
        className={
          "relative max-w-[min(100%,28rem)] sm:max-w-[min(100%,32rem)] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed " +
          (isUser
            ? "bg-zinc-100 text-zinc-900 rounded-br-md"
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
            className="mb-2 max-h-40 rounded-lg border border-zinc-700 object-cover"
          />
        ) : null}

        <div className="whitespace-pre-wrap break-words">{content}</div>

        {(timestamp || status || isStreaming) && (
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] tracking-wide text-zinc-500">
            {timestamp ? <span>{timestamp}</span> : null}
            {status ? <span>{status}</span> : null}
            {isStreaming ? <span className="animate-pulse">streaming…</span> : null}
          </div>
        )}

        {!isUser && !isError && content ? (
          <div className="mt-2 flex flex-wrap items-center gap-1 opacity-70 transition-opacity group-hover:opacity-100">
            <button type="button" onClick={handleCopy} className="rounded-md border border-zinc-700 px-2 py-1 text-[10px] tracking-wide text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" title="Copy">{copied ? "Copied" : "Copy"}</button>
            <button type="button" onClick={() => setLiked((v) => (v === "up" ? null : "up"))} className={"rounded-md border px-2 py-1 text-[10px] tracking-wide " + (liked === "up" ? "border-zinc-500 text-zinc-200 bg-zinc-800" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800")} title="Like">Like</button>
            <button type="button" onClick={() => setLiked((v) => (v === "down" ? null : "down"))} className={"rounded-md border px-2 py-1 text-[10px] tracking-wide " + (liked === "down" ? "border-zinc-500 text-zinc-200 bg-zinc-800" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800")} title="Dislike">Dislike</button>
            <button type="button" onClick={handleShare} className="rounded-md border border-zinc-700 px-2 py-1 text-[10px] tracking-wide text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" title="Share">{shared ? "Shared" : "Share"}</button>
            <button type="button" onClick={handleSave} className={"rounded-md border px-2 py-1 text-[10px] tracking-wide " + (saved ? "border-zinc-500 text-zinc-200 bg-zinc-800" : "border-zinc-700 text-zinc-400 hover:bg-zinc-800")} title="Save">{saved ? "Saved" : "Save"}</button>
            {onSpeak ? (<button type="button" onClick={onSpeak} className="rounded-md border border-zinc-700 px-2 py-1 text-[10px] tracking-wide text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" title="Speak">Speak</button>) : null}
            {onRegenerate ? (<button type="button" onClick={onRegenerate} className="rounded-md border border-zinc-700 px-2 py-1 text-[10px] tracking-wide text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200" title="Regenerate">Retry</button>) : null}
          </div>
        ) : null}
      </div>
    </div>
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
  const phaseLabel = labels[phase] || "Thinking";
  const antennaClass = phase === "responding" ? "animate-ping" : "animate-pulse";
  const stemClass = phase === "reading" ? "rotate-[-18deg]" : phase === "responding" ? "rotate-[18deg]" : "";
  const headClass =
    phase === "reading"
      ? "animate-[bounce_1.4s_ease-in-out_infinite]"
      : phase === "thinking"
        ? "animate-[pulse_1.1s_ease-in-out_infinite]"
        : phase === "searching"
          ? "animate-[spin_1.8s_linear_infinite]"
          : "animate-[bounce_0.7s_ease-in-out_infinite]";
  const eyeLeft = phase === "responding" ? "animate-ping" : "";
  const eyeRight = phase === "thinking" ? "animate-pulse" : "";
  const barWidth = phase === "reading" ? "w-1/4" : phase === "thinking" ? "w-1/2" : phase === "searching" ? "w-3/4" : "w-full";

  return (
    <div className="flex items-start gap-3 py-2 px-1">
      <div className="relative w-8 h-8 shrink-0 rounded-xl bg-zinc-800 border border-zinc-700 flex items-center justify-center overflow-hidden" aria-label={phaseLabel} title={phaseLabel}>
        <span className={"absolute -top-1 left-1/2 w-1.5 h-1.5 -translate-x-1/2 rounded-full bg-zinc-300 " + antennaClass} />
        <span className={"absolute top-0.5 left-1/2 h-1.5 w-px -translate-x-1/2 bg-zinc-500 " + stemClass} />
        <div className={"relative w-5 h-4 rounded-[6px] border border-zinc-400 bg-zinc-700 flex items-center justify-center gap-0.5 transition-transform " + headClass}>
          <span className={"w-1 h-1 rounded-full bg-zinc-200 " + eyeLeft} />
          <span className={"w-1 h-1 rounded-full bg-zinc-200 " + eyeRight} />
        </div>
        <span className="absolute bottom-1 w-3 h-px bg-zinc-400 rounded-full" />
      </div>
      <div className="flex flex-col gap-1 pt-0.5">
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <span className="font-medium text-zinc-300">{phaseLabel}</span>
          <span className="inline-flex gap-0.5 ml-0.5">
            <span className="w-1 h-1 rounded-full bg-zinc-500 animate-bounce" />
            <span className="w-1 h-1 rounded-full bg-zinc-500 animate-bounce [animation-delay:150ms]" />
            <span className="w-1 h-1 rounded-full bg-zinc-500 animate-bounce [animation-delay:300ms]" />
          </span>
        </div>
        <div className="h-1 w-28 rounded-full bg-zinc-800 overflow-hidden">
          <div className={"h-full rounded-full bg-zinc-400 transition-all animate-pulse " + barWidth} />
        </div>
      </div>
    </div>
  );
}

export default ChatMessage;
