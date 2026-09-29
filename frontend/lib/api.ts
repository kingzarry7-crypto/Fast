// frontend/lib/api.ts
// KING ZARRY AI — complete API client (auth, chat, admin, agent, TTS, billing, markets)

import type {
  AuthUser,
  AuthResponse,
  MeResponse,
  ChatResponse,
  ApiErrorData,
} from "@/types";

function getBaseUrl(): string {
  // Same-origin mode: browser calls /api on Vercel; next.config rewrites to Railway.
  // Required for mobile — cross-site cookies (vercel.app → railway.app) are blocked.
  const sameOrigin =
    (process.env.NEXT_PUBLIC_API_SAME_ORIGIN || "true").trim().toLowerCase() === "true" ||
    (process.env.NEXT_PUBLIC_API_SAME_ORIGIN || "").trim() === "1";
  if (sameOrigin) return "";
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
            if (typeof d.detail === "string") detail = d.detail;
            raw = json;
          } else {
            message = text.slice(0, 500) || message;
          }
        } catch {
          message = text.slice(0, 500) || message;
        }
      }
    } catch {
      /* ignore */
    }

    throw new ApiError({ status: response.status, message, detail, raw });
  }

  try {
    return (await response.json()) as T;
  } catch (error: unknown) {
    throw new ApiError({
      status: response.status,
      message: "Invalid JSON response",
      raw: error,
    });
  }
}

function requireUser(data: AuthResponse | MeResponse): AuthUser {
  if (!data?.user) throw new ApiError({ status: 500, message: "Invalid user response" });
  return data.user;
}

export async function login(email: string, password: string, signal?: AbortSignal): Promise<AuthResponse> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail || !password) throw new ApiError({ status: 400, message: "Email and password required" });
  return request<AuthResponse>("/api/auth/login", { method: "POST", body: { email: normalizedEmail, password }, signal });
}

export type RegisterResult = AuthResponse & {
  requires_verification?: boolean;
  email?: string;
  message?: string;
  dev_code?: string;
};

export async function register(
  email: string,
  password: string,
  username?: string,
  displayName?: string,
  signal?: AbortSignal
): Promise<RegisterResult> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail || !password) throw new ApiError({ status: 400, message: "Email and password required" });
  const payload: Record<string, string> = { email: normalizedEmail, password };
  if (username) payload.username = username;
  if (displayName) payload.display_name = displayName;
  return request<RegisterResult>("/api/auth/register", { method: "POST", body: payload, signal });
}

export async function verifyEmail(email: string, code: string, signal?: AbortSignal): Promise<AuthResponse> {
  const normalizedEmail = email.trim().toLowerCase();
  const trimmedCode = code.trim();
  if (!normalizedEmail || !trimmedCode) throw new ApiError({ status: 400, message: "Email and verification code required" });
  return request<AuthResponse>("/api/auth/verify-email", { method: "POST", body: { email: normalizedEmail, code: trimmedCode }, signal });
}

export async function resendVerificationCode(email: string, signal?: AbortSignal) {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail) throw new ApiError({ status: 400, message: "Email required" });
  return request<{ status: string; message?: string; dev_code?: string }>("/api/auth/resend-code", { method: "POST", body: { email: normalizedEmail }, signal });
}

export async function forgotPassword(email: string, signal?: AbortSignal) {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail) throw new ApiError({ status: 400, message: "Email required" });
  return request<{ status: string; message?: string; dev_code?: string }>("/api/auth/forgot-password", { method: "POST", body: { email: normalizedEmail }, signal });
}

export async function resetPassword(email: string, code: string, newPassword: string, signal?: AbortSignal) {
  const normalizedEmail = email.trim().toLowerCase();
  const trimmedCode = code.trim();
  if (!normalizedEmail || !trimmedCode || !newPassword) throw new ApiError({ status: 400, message: "Email, code, and new password required" });
  return request<{ status: string; message?: string }>("/api/auth/reset-password", {
    method: "POST",
    body: { email: normalizedEmail, code: trimmedCode, new_password: newPassword },
    signal,
  });
}

export async function me(signal?: AbortSignal): Promise<MeResponse> {
  return request<MeResponse>("/api/auth/me", { signal });
}

export async function logout(signal?: AbortSignal): Promise<void> {
  await request<unknown>("/api/auth/logout", { method: "POST", signal });
}

export async function chat(
  message: string,
  options?: { conversation_id?: string | null; image_base64?: string; image_mime?: string; signal?: AbortSignal }
): Promise<ChatResponse> {
  const body: Record<string, unknown> = { message };
  if (options?.conversation_id) body.conversation_id = options.conversation_id;
  if (options?.image_base64) {
    body.image_base64 = options.image_base64;
    body.image_mime = options.image_mime || "image/jpeg";
  }
  return request<ChatResponse>("/api/chat", { method: "POST", body, signal: options?.signal });
}

export type ConversationItem = {
  id: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
};

export async function listConversations(signal?: AbortSignal): Promise<ConversationItem[]> {
  const data = await request<{ conversations?: ConversationItem[] } | ConversationItem[]>("/api/conversations", { signal });
  if (Array.isArray(data)) return data;
  return (data as { conversations?: ConversationItem[] }).conversations || [];
}

export async function createConversation(signal?: AbortSignal): Promise<ConversationItem> {
  return request<ConversationItem>("/api/conversations", { method: "POST", body: {}, signal });
}

export async function getConversationMessages(
  conversationId: string,
  signal?: AbortSignal
): Promise<Array<{ id?: string; role?: string; content?: string; created_at?: string }>> {
  const data = await request<
    | { messages?: Array<{ id?: string; role?: string; content?: string; created_at?: string }> }
    | Array<{ id?: string; role?: string; content?: string; created_at?: string }>
  >(`/api/conversations/${conversationId}/messages`, { signal });
  if (Array.isArray(data)) return data;
  return (data as { messages?: Array<{ id?: string; role?: string; content?: string; created_at?: string }> }).messages || [];
}

export type MarketSnapshot = {
  symbol?: string;
  price?: number;
  change?: number;
  signal?: string;
  trend?: string;
  [key: string]: unknown;
};

export async function getMarkets(signal?: AbortSignal) {
  return request<{ symbols?: MarketSnapshot[]; count?: number }>("/api/markets", { signal });
}

export async function getSignals(signal?: AbortSignal) {
  return request<{ signals?: MarketSnapshot[]; actionable_count?: number }>("/api/signals", { signal });
}

export async function getNews(signal?: AbortSignal) {
  return request<{ items?: unknown[] }>("/api/news", { signal });
}

export const api = {
  login,
  register,
  verifyEmail,
  resendVerificationCode,
  forgotPassword,
  resetPassword,
  me,
  logout,
  chat,
  listConversations,
  createConversation,
  getConversationMessages,
  getMarkets,
  getSignals,
  getNews,
};

export default api;
