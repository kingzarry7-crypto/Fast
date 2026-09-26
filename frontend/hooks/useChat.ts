"use client";

import { useCallback, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ChatMessage } from "@/types";
import {
  detectChatIntent,
  upgradeMessageForIntent,
} from "@/lib/chatIntent";
import {
  FREE_DAILY_MESSAGE_LIMIT,
  getFreeMessageCount,
  getIsVip,
  incrementFreeMessageCount,
} from "@/lib/membership";

export interface SendImage {
  base64: string;
  mime: string;
  previewUrl?: string;
  name?: string;
}

export function useChat(userId?: string | null, serverSubscribed?: boolean) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const now = () => {
    const d = new Date();
    return `${d.getHours().toString().padStart(2, "0")}:${d
      .getMinutes()
      .toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
  };

  const send = useCallback(
    async (text: string, capability = "AI", image?: SendImage) => {
      const trimmed = text.trim();
      const hasImage = !!(image && image.base64);
      if ((!trimmed && !hasImage) || sending) return;

      const effectiveText =
        trimmed || (hasImage ? "What do you see in this image?" : "");

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        text: effectiveText,
        timestamp: now(),
        imagePreviewUrl: image?.previewUrl,
        imageName: image?.name,
      };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);
      setError(null);

      const isVip = Boolean(serverSubscribed) || getIsVip();
      const intent = detectChatIntent(effectiveText);

      if (!isVip && intent !== "normal") {
        const aiMsg: ChatMessage = {
          id: `gate-${Date.now()}`,
          role: "assistant",
          text: upgradeMessageForIntent(intent),
          timestamp: now(),
          status: "MEMBERSHIP • UPGRADE REQUIRED",
          capability: "VIP",
        };
        setMessages((prev) => [...prev, aiMsg]);
        setSending(false);
        return;
      }

      if (!isVip && intent === "normal") {
        const used = getFreeMessageCount(userId);
        if (used >= FREE_DAILY_MESSAGE_LIMIT) {
          const aiMsg: ChatMessage = {
            id: `limit-${Date.now()}`,
            role: "assistant",
            text: [
              `Daily free chat limit reached (${FREE_DAILY_MESSAGE_LIMIT} messages).`,
              "",
              "Upgrade to VIP for unlimited chat, signals, plans, and alerts.",
              "→ Pricing · or confirm Telegram payment under Settings.",
            ].join("\n"),
            timestamp: now(),
            status: "MEMBERSHIP • DAILY LIMIT",
            capability: "LIMIT",
          };
          setMessages((prev) => [...prev, aiMsg]);
          setSending(false);
          return;
        }
      }

      abortRef.current?.abort();
      abortRef.current = new AbortController();

      try {
        const res = await api.sendChatMessage(
          effectiveText,
          image ? { base64: image.base64, mime: image.mime } : undefined,
          abortRef.current.signal
        );

        if (!isVip) {
          incrementFreeMessageCount(userId);
        }

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
        if (err instanceof ApiError && err.status === 401)
          message = "Session expired. Please sign in again.";
        if (err instanceof ApiError && err.status === 403)
          message = err.detail || "Access denied.";

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
    [sending, userId, serverSubscribed]
  );

  const clear = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
  }, []);

  return { messages, sending, error, send, clear };
}
