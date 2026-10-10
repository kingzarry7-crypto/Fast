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

export function useChat(
  userId?: string | null,
  serverSubscribed?: boolean,
  conversationId?: string | null
) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const agentPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const conversationIdRef = useRef<string | null | undefined>(conversationId);
  conversationIdRef.current = conversationId;

  const now = () => {
    const d = new Date();
    return `${d.getHours().toString().padStart(2, "0")}:${d
      .getMinutes()
      .toString()
      .padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
  };

  const extractApproval = (reply: string) => {
    const match = reply.match(
      /(?:Approval ID|approval id)\s*[:=]\s*([0-9a-f]{8}-[0-9a-f-]{27,36})/i,
    );
    if (!match) return undefined;
    const lower = reply.toLowerCase();
    const operation = lower.includes("calendar")
      ? "create_calendar_event"
      : lower.includes("drive")
        ? "upload_drive_text"
        : "send_gmail";
    return { id: match[1], provider: "google" as const, operation };
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
        const shouldStream = intent === "normal" && !hasImage;

        if (shouldStream) {
          const aiId = "ai-" + Date.now();
          setMessages((prev) => [
            ...prev,
            {
              id: aiId,
              role: "assistant",
              text: "",
              timestamp: now(),
              status: "",
              capability,
            },
          ]);

          try {
            const streamed = await api.streamChatMessage(effectiveText, {
              conversationId: conversationIdRef.current || undefined,
              signal: abortRef.current.signal,
              onDelta: (delta) => {
                setMessages((prev) =>
                  prev.map((item) =>
                    item.id === aiId
                      ? { ...item, text: (item.text || "") + delta, status: "" }
                      : item
                  )
                );
              },
              onStart: (provider) => {
                setMessages((prev) =>
                  prev.map((item) =>
                    item.id === aiId
                      ? { ...item, status: provider === "kz_agent" ? "KZ AGENT • STARTING" : "" }
                      : item
                  )
                );
              },
              onAgent: (agent) => {
                setMessages((prev) =>
                  prev.map((item) =>
                    item.id === aiId
                      ? { ...item, status: agent.activity ? `KZ AGENT • ${agent.activity}` : "KZ AGENT • WORKING" }
                      : item
                  )
                );
              },
            });

            if (!isVip) incrementFreeMessageCount(userId);
            if (streamed.conversation_id && !conversationIdRef.current) {
              conversationIdRef.current = streamed.conversation_id;
            }
            setMessages((prev) =>
              prev.map((item) =>
                item.id === aiId
                  ? { ...item, text: streamed.reply, status: streamed.agent?.id ? "KZ AGENT • WORKING" : "AI CORE • RESPONSE RECEIVED", approval: streamed.approval || extractApproval(streamed.reply) }
                  : item
              )
            );

            if (streamed.agent?.id) {
              const agentId = streamed.agent.id;
              if (agentPollRef.current) clearInterval(agentPollRef.current);
              agentPollRef.current = setInterval(async () => {
                try {
                  const live = await api.getKZAgentStatus(agentId);
                  const state = live.agent;
                  if (!state) return;
                  const terminal = ["completed", "failed", "paused"].includes(String(state.status || ""));
                  setMessages((prev) =>
                    prev.map((item) =>
                      item.id === aiId
                        ? {
                            ...item,
                            status: terminal
                              ? `KZ AGENT • ${String(state.status || "").replaceAll("_", " ").toUpperCase()}`
                              : `KZ AGENT • ${state.activity || "WORKING"}`,
                          }
                        : item
                    )
                  );
                  if (terminal && agentPollRef.current) {
                    clearInterval(agentPollRef.current);
                    agentPollRef.current = null;
                  }
                } catch {
                  // A temporary status poll failure must never interrupt the mission.
                }
              }, 2000);
            }
            void api
              .generateChatSuggestions(effectiveText, streamed.reply, abortRef.current?.signal)
              .then((result) => {
                if (!result.suggestions?.length) return;
                setMessages((prev) =>
                  prev.map((item) =>
                    item.id === aiId ? { ...item, suggestions: result.suggestions } : item
                  )
                );
              })
              .catch(() => {});
            return streamed;
          } catch (streamErr) {
            if (streamErr instanceof DOMException && streamErr.name === "AbortError") return;
            setMessages((prev) => prev.filter((item) => item.id !== aiId));
          }
        }

        const res = await api.sendChatMessage(
          effectiveText,
          image ? { base64: image.base64, mime: image.mime } : undefined,
          abortRef.current.signal,
          conversationIdRef.current || undefined
        );

        if (!isVip) {
          incrementFreeMessageCount(userId);
        }

        if (res.conversation_id && !conversationIdRef.current) {
          conversationIdRef.current = res.conversation_id;
        }

        const aiMsg: ChatMessage = {
          id: "ai-" + Date.now(),
          role: "assistant",
          text: res.reply,
          timestamp: now(),
          status: "AI CORE • RESPONSE RECEIVED",
          capability,
        };
        setMessages((prev) => [...prev, aiMsg]);
        void api
          .generateChatSuggestions(effectiveText, res.reply, abortRef.current?.signal)
          .then((result) => {
            if (!result.suggestions?.length) return;
            setMessages((prev) =>
              prev.map((item) =>
                item.id === aiMsg.id ? { ...item, suggestions: result.suggestions } : item
              )
            );
          })
          .catch(() => {});
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

  const decideApproval = useCallback(async (
    messageId: string,
    decision: "once" | "always" | "reject",
  ) => {
    const current = messages.find((item) => item.id === messageId);
    if (!current?.approval) return;
    try {
      const result = await api.decideGoogleApproval(current.approval.id, decision);
      setMessages((prev) => prev.map((item) =>
        item.id === messageId
          ? {
              ...item,
              approval: undefined,
              status: result.status === "completed" && result.verified === true
                ? "AI CORE • ACTION VERIFIED"
                : result.status === "completed"
                  ? "AI CORE • ACTION COMPLETED (UNVERIFIED)"
                  : result.status === "rejected"
                    ? "AI CORE • ACTION REJECTED"
                    : "AI CORE • APPROVAL SAVED",
              text: result.status === "completed" && result.verified === true
                ? `${item.text}\n\n✓ Action completed and verification evidence was received.`
                : result.status === "completed"
                  ? `${item.text}\n\nThe backend reported completion, but did not return verification evidence. Check the destination before relying on this result.`
                  : result.status === "rejected"
                    ? `${item.text}\n\nAction rejected. Nothing was sent.`
                    : `${item.text}\n\n✓ Allowed always. The current action was completed${result.permission_saved === false ? ", but the saved permission could not be stored." : " and this permission was saved."}`,
            }
          : item
      ));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Approval failed";
      setError(message);
    }
  }, [messages]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (agentPollRef.current) {
      clearInterval(agentPollRef.current);
      agentPollRef.current = null;
    }
    setSending(false);
    setMessages((prev) =>
      prev.map((item) =>
        item.role === "assistant" && item.status === ""
          ? { ...item, status: "AI CORE • STOPPED" }
          : item
      )
    );
  }, []);

  const clear = useCallback(() => {
    abortRef.current?.abort();
    if (agentPollRef.current) {
      clearInterval(agentPollRef.current);
      agentPollRef.current = null;
    }
    abortRef.current = null;
    setMessages([]);
    setError(null);
    setSending(false);
  }, []);

  return { messages, setMessages, sending, error, send, decideApproval, stop, clear };
}
