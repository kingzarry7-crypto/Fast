// Fast/frontend/lib/api.ts
// KING ZARRY AI — API client.

import type {
  AuthUser,
  AuthResponse,
  MeResponse,
  ChatResponse,
  ApiErrorData,
} from "@/types";

function getBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!raw) return "";
  return raw.trim().replace(/\/+$/, "");
}

function buildUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const base = getBaseUrl();
  return base ? `${base}${normalized}` : normalized;
}

export class ApiError extends Error {
  status: number;
  detail?: string;
  raw?: unknown;

  constructor(data: ApiErrorData) {
    super(data.message);
    this.name = "ApiError";
    this.status = data.status;
    this.detail = data.detail;
    this.raw = data.raw;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, signal, headers = {} } = options;
  const url = buildUrl(path);
  const hasBody = body !== undefined && method !== "GET";

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };
  if (hasBody && !finalHeaders["Content-Type"]) {
    finalHeaders["Content-Type"] = "application/json";
  }

  let fetchBody: string | undefined;
  if (hasBody) {
    try {
      fetchBody = JSON.stringify(body);
    } catch {
      throw new ApiError({ status: 400, message: "Invalid request body" });
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: finalHeaders,
      body: fetchBody,
      credentials: "include",
      signal,
    });
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    const message = error instanceof Error ? error.message : "Network error";
    throw new ApiError({ status: 0, message, raw: error });
  }

  if (response.status === 204) return undefined as T;

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let detail: string | undefined;
    let raw: unknown;

    try {
      const text = await response.text();
      if (text) {
        try {
          const json: unknown = JSON.parse(text);
          if (json && typeof json === "object" && !Array.isArray(json)) {
            const d = json as Record<string, unknown>;
            message =
              (typeof d.detail === "string" && d.detail) ||
              (typeof d.message === "string" && d.message) ||
              message;
            detail = typeof d.detail === "string" ? d.detail : undefined;
            raw = d;
          } else {
            raw = json;
          }
        } catch {
          message = text.slice(0, 500) || message;
          raw = text;
        }
      }
    } catch {
      // ignore
    }

    throw new ApiError({ status: response.status, message, detail, raw });
  }

  const text = await response.text();
  if (!text) return undefined as T;

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError({
      status: response.status,
      message: "Invalid JSON response",
      raw: text,
    });
  }
}

export async function getCurrentUser(signal?: AbortSignal): Promise<AuthUser> {
  const data = await request<MeResponse>("/api/auth/me", {
    method: "GET",
    signal,
  });
  if (!data?.user) {
    throw new ApiError({ status: 500, message: "Invalid user response" });
  }
  return data.user;
}

export async function login(
  email: string,
  password: string,
  signal?: AbortSignal
): Promise<AuthResponse> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail || !password) {
    throw new ApiError({ status: 400, message: "Email and password required" });
  }
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: { email: normalizedEmail, password },
    signal,
  });
}

export async function register(
  email: string,
  password: string,
  username?: string,
  displayName?: string,
  signal?: AbortSignal
): Promise<AuthResponse> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail || !password) {
    throw new ApiError({ status: 400, message: "Email and password required" });
  }
  const payload: Record<string, string> = {
    email: normalizedEmail,
    password,
  };
  if (username?.trim()) payload.username = username.trim();
  if (displayName?.trim()) payload.display_name = displayName.trim();

  return request<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: payload,
    signal,
  });
}

export async function logout(
  signal?: AbortSignal
): Promise<{ status: string; message?: string }> {
  return request("/api/auth/logout", { method: "POST", signal });
}

export interface SendImagePayload {
  base64: string;
  mime: string;
}

export async function sendChatMessage(
  message: string,
  image?: SendImagePayload,
  signal?: AbortSignal,
  conversationId?: string | null
): Promise<ChatResponse> {
  const trimmed = message.trim();
  const hasImage = !!(image && image.base64);

  if (!trimmed && !hasImage) {
    throw new ApiError({ status: 400, message: "Message required" });
  }
  if (trimmed.length > 4000) {
    throw new ApiError({ status: 400, message: "Message too long" });
  }

  const body: Record<string, unknown> = {
    message: trimmed || "What do you see in this image?",
  };
  if (conversationId) {
    body.conversation_id = conversationId;
  }
  if (hasImage) {
    body.image_base64 = image!.base64;
    body.image_mime = image!.mime || "image/jpeg";
  }

  const data = await request<ChatResponse>("/api/chat", {
    method: "POST",
    body,
    signal,
  });
  if (!data?.reply) {
    throw new ApiError({ status: 500, message: "Invalid chat response" });
  }
  return data;
}

export async function healthCheck(): Promise<{
  status: string;
  database?: { status: string };
}> {
  return request("/health", { method: "GET" });
}

export async function createCheckoutSession(
  plan: string,
  signal?: AbortSignal
): Promise<{ status: string; checkout_url: string; session_id?: string }> {
  return request("/api/billing/create-checkout-session", {
    method: "POST",
    body: { plan },
    signal,
  });
}

export interface AdminStats {
  status: string;
  active_subscribers: number;
  payments_count: number;
  revenue_cents: number;
  revenue_usd: number;
  recent_payments: Array<{
    email?: string;
    plan?: string;
    amount_cents?: number;
    status?: string;
    created_at?: string;
  }>;
}

export async function getAdminStats(
  signal?: AbortSignal
): Promise<AdminStats> {
  return request("/api/admin/stats", { method: "GET", signal });
}

export interface ConversationItem {
  id: string;
  title: string;
  preview?: string;
  created_at?: string;
  updated_at?: string;
}

export async function listConversations(
  signal?: AbortSignal
): Promise<ConversationItem[]> {
  const data = await request<{ status: string; conversations: ConversationItem[] }>(
    "/api/conversations",
    { method: "GET", signal }
  );
  return data?.conversations || [];
}

export async function createConversation(
  signal?: AbortSignal
): Promise<ConversationItem> {
  const data = await request<{ status: string; conversation: ConversationItem }>(
    "/api/conversations",
    { method: "POST", signal }
  );
  if (!data?.conversation?.id) {
    throw new ApiError({ status: 500, message: "Could not create conversation" });
  }
  return data.conversation;
}

export async function getConversationMessages(
  conversationId: string,
  signal?: AbortSignal
): Promise<{ role: string; content: string; created_at?: string; id?: string }[]> {
  const data = await request<{
    status: string;
    messages: { role: string; content: string; created_at?: string; id?: string }[];
  }>(`/api/conversations/${encodeURIComponent(conversationId)}/messages`, {
    method: "GET",
    signal,
  });
  return data?.messages || [];
}

export const api = {
  buildUrl,
  getBaseUrl,
  getCurrentUser,
  me: getCurrentUser,
  login,
  register,
  logout,
  sendChatMessage,
  healthCheck,
  createCheckoutSession,
  getAdminStats,
  listConversations,
  createConversation,
  getConversationMessages,
};

export type {
  AuthUser,
  AuthResponse,
  MeResponse,
  ChatResponse,
  ApiErrorData,
} from "@/types";
