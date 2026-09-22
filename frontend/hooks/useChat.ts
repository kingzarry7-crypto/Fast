"use client";

import { useCallback, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ChatMessage } from "@/types";

export interface SendImage {
  base64: string;
  mime: string;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const now = () => {
    const d = new Date();
    return `${d.getHours().toString().padStart(2, "0")}:${d
      .getMinutes()
      .toString()
      .padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
  };

  const send = useCallback(
    async (text: string, capability = "AI", image?: SendImage) => {
      const trimmed = text.trim();
      const hasImage = !!(image && image.base64);

      // Allow image-only messages
      if ((!trimmed && !hasImage) || sending) return;

      const effectiveText = trimmed || (hasImage ? "What do you see in this image?" : "");

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        text: effectiveText,
        timestamp: now(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);
      setError(null);

      abortRef.current?.abort();
      abortRef.current = new AbortController();

      try {
        const res = await api.sendChatMessage(
          effectiveText,
          image,
          abortRef.current.signal
        );
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: "assistant",
          text: res.reply,
          timestamp: now(),
          status: "AI CORE • RESPONSE RECEIVED",
          capability,
        };
        setMessages((prev) => [...prev, aiMsg]);
        return res;
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;

        let message =
          err instanceof Error ? err.message : "Unable to reach backend.";

        if (err instanceof ApiError && err.status === 401) {
          message = "Session expired. Please sign in again.";
        }
        if (err instanceof ApiError && err.status === 403) {
          message = err.detail || "Access denied.";
        }

        setError(message);
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: "assistant",
            text: message,
            timestamp: now(),
            status: "AI CORE • BACKEND ERROR",
            capability: "SYSTEM",
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [sending]
  );

  const clear = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
  }, []);

  return { messages, sending, error, send, clear };
}
