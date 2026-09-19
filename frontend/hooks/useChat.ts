// Fast/frontend/hooks/useChat.ts
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  created_at?: string;
  conversation_id?: string;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (
    content: string
  ) => Promise<{ success: boolean; message?: ChatMessage; error?: string }>;
  clearMessages: () => void;
  retryLastMessage: () => Promise<{ success: boolean; error?: string }>;
}

// -----------------------------------------------------------------------------
// API response types
// -----------------------------------------------------------------------------

interface ChatApiResponse {
  status?: string;
  reply?: string;
  conversation_id?: string;
}

interface ApiErrorResponse {
  detail?: string;
  message?: string;
  error?: string;
}

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  return base.replace(/\/$/, "");
}

function generateId(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function getErrorMessage(
  status: number,
  data: ApiErrorResponse | null,
  fallback: string
): string {
  if (status === 401 || status === 403) {
    return "Authentication required. Please sign in again.";
  }

  if (typeof data?.detail === "string" && data.detail.trim()) {
    return data.detail;
  }

  if (typeof data?.message === "string" && data.message.trim()) {
    return data.message;
  }

  if (typeof data?.error === "string" && data.error.trim()) {
    return data.error;
  }

  return fallback;
}

function getReply(data: ChatApiResponse | null): string | null {
  if (typeof data?.reply !== "string") {
    return null;
  }

  const reply = data.reply.trim();

  return reply || null;
}

async function parseJsonResponse<T>(
  response: Response
): Promise<T | null> {
  const text = await response.text();

  if (!text.trim()) {
    return null;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

// -----------------------------------------------------------------------------
// Hook
// -----------------------------------------------------------------------------

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mountedRef = useRef(false);
  const requestIdRef = useRef(0);
  const loadingRef = useRef(false);

  const lastUserMessageRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // ---------------------------------------------------------------------------
  // Mount / unmount protection
  // ---------------------------------------------------------------------------

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;

      requestIdRef.current += 1;

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Loading state helper
  // ---------------------------------------------------------------------------

  const setLoading = useCallback((value: boolean) => {
    loadingRef.current = value;

    if (mountedRef.current) {
      setIsLoading(value);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Clear local conversation
  // ---------------------------------------------------------------------------

  const clearMessages = useCallback(() => {
    requestIdRef.current += 1;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    loadingRef.current = false;

    setMessages([]);
    setError(null);
    setIsLoading(false);

    lastUserMessageRef.current = null;
  }, []);

  // ---------------------------------------------------------------------------
  // Send message
  // ---------------------------------------------------------------------------

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();

      if (!trimmed) {
        return {
          success: false,
          error: "Message cannot be empty.",
        };
      }

      if (loadingRef.current) {
        return {
          success: false,
          error: "Please wait for the current response.",
        };
      }

      const requestId = ++requestIdRef.current;

      // Cancel any previous request just in case.
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };

      lastUserMessageRef.current = trimmed;

      setError(null);
      setMessages((previous) => [...previous, userMessage]);
      setLoading(true);

      try {
        const base = getApiBase();

        const response = await fetch(`${base}/api/chat`, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: trimmed,
          }),
          signal: controller.signal,
        });

        const data = await parseJsonResponse<ChatApiResponse & ApiErrorResponse>(
          response
        );

        // Ignore responses belonging to an older request.
        if (requestId !== requestIdRef.current) {
          return {
            success: false,
          };
        }

        if (!response.ok) {
          const message = getErrorMessage(
            response.status,
            data,
            `Chat request failed (${response.status}).`
          );

          if (mountedRef.current) {
            setError(message);
          }

          return {
            success: false,
            error: message,
          };
        }

        const reply = getReply(data);

        if (!reply) {
          const message = "The AI returned an invalid response.";

          if (mountedRef.current) {
            setError(message);
          }

          return {
            success: false,
            error: message,
          };
        }

        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: "assistant",
          content: reply,
          created_at: new Date().toISOString(),
          conversation_id:
            typeof data?.conversation_id === "string"
              ? data.conversation_id
              : undefined,
        };

        if (requestId !== requestIdRef.current) {
          return {
            success: false,
          };
        }

        if (mountedRef.current) {
          setMessages((previous) => [...previous, assistantMessage]);
          setError(null);
        }

        return {
          success: true,
          message: assistantMessage,
        };
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return {
            success: false,
            error: "Request cancelled.",
          };
        }

        if (requestId !== requestIdRef.current) {
          return {
            success: false,
          };
        }

        const message =
          error instanceof Error && error.message
            ? error.message
            : "Failed to send message.";

        if (mountedRef.current) {
          setError(message);
        }

        return {
          success: false,
          error: message,
        };
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }

        if (requestId === requestIdRef.current) {
          setLoading(false);
        }
      }
    },
    [setLoading]
  );

  // ---------------------------------------------------------------------------
  // Retry last user message
  // ---------------------------------------------------------------------------

  const retryLastMessage = useCallback(async () => {
    const lastUserMessage = lastUserMessageRef.current;

    if (!lastUserMessage) {
      return {
        success: false,
        error: "No message to retry.",
      };
    }

    if (loadingRef.current) {
      return {
        success: false,
        error: "Please wait for the current response.",
      };
    }

    const requestId = ++requestIdRef.current;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setError(null);
    setLoading(true);

    try {
      const base = getApiBase();

      const response = await fetch(`${base}/api/chat`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: lastUserMessage,
        }),
        signal: controller.signal,
      });

      const data = await parseJsonResponse<ChatApiResponse & ApiErrorResponse>(
        response
      );

      if (requestId !== requestIdRef.current) {
        return {
          success: false,
        };
      }

      if (!response.ok) {
        const message = getErrorMessage(
          response.status,
          data,
          `Retry failed (${response.status}).`
        );

        if (mountedRef.current) {
          setError(message);
        }

        return {
          success: false,
          error: message,
        };
      }

      const reply = getReply(data);

      if (!reply) {
        const message = "The AI returned an invalid response.";

        if (mountedRef.current) {
          setError(message);
        }

        return {
          success: false,
          error: message,
        };
      }

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: reply,
        created_at: new Date().toISOString(),
        conversation_id:
          typeof data?.conversation_id === "string"
            ? data.conversation_id
            : undefined,
      };

      if (requestId !== requestIdRef.current) {
        return {
          success: false,
        };
      }

      if (mountedRef.current) {
        setMessages((previous) => [...previous, assistantMessage]);
        setError(null);
      }

      return {
        success: true,
      };
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return {
          success: false,
          error: "Request cancelled.",
        };
      }

      if (requestId !== requestIdRef.current) {
        return {
          success: false,
        };
      }

      const message =
        error instanceof Error && error.message
          ? error.message
          : "Retry failed.";

      if (mountedRef.current) {
        setError(message);
      }

      return {
        success: false,
        error: message,
      };
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }

      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [setLoading]);

  // ---------------------------------------------------------------------------
  // Return public API
  // ---------------------------------------------------------------------------

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    retryLastMessage,
  };
}

export default useChat;
