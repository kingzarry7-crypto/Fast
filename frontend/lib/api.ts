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
  const sameOrigin =
    (process.env.NEXT_PUBLIC_API_SAME_ORIGIN || "true").trim().toLowerCase() === "true" ||
    (process.env.NEXT_PUBLIC_API_SAME_ORIGIN || "").trim() === "1";
  if (sameOrigin) return "";
  const raw = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim().replace(/\/+$/, "");
  return raw;
}

function buildUrl(path: string): string {
  const base = getBaseUrl();
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

export class ApiError extends Error {
  status: number;
  detail?: string;
  raw?: unknown;
  constructor(data: ApiErrorData) {
    super(data.message || "Request failed");
    this.name = "ApiError";
    this.status = data.status;
    this.detail = data.detail;
    this.raw = data.raw;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers || {}),
  };
  let fetchBody: string | undefined;
  if (options.body !== undefined && method !== "GET" && method !== "HEAD") {
    headers["Content-Type"] = "application/json";
    try {
      fetchBody = JSON.stringify(options.body);
    } catch {
      throw new ApiError({ status: 400, message: "Invalid request body" });
    }
  }
  const url = buildUrl(path);
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: fetchBody,
      credentials: "include",
      signal: options.signal,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Network error — is the API reachable?";
    throw new ApiError({ status: 0, message, raw: error });
  }
  const contentType = response.headers.get("content-type") || "";
  let data: unknown = null;
  if (contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      const text = await response.text();
      data = text || null;
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    const obj = data && typeof data === "object" ? (data as Record<string, unknown>) : null;
    const detail =
      (obj && (typeof obj.detail === "string" ? obj.detail : undefined)) ||
      (obj && typeof obj.message === "string" ? obj.message : undefined) ||
      undefined;
    const message =
      detail ||
      (typeof data === "string" && data) ||
      response.statusText ||
      `HTTP ${response.status}`;
    throw new ApiError({ status: response.status, message, detail, raw: data });
  }
  return data as T;
}

function normalizeUser(user: AuthUser | undefined | null): AuthUser | null {
  if (!user) return null;
  return user;
}

export async function getMe(signal?: AbortSignal): Promise<MeResponse> {
  const data = await request<MeResponse>("/api/auth/me", { method: "GET", signal });
  if (!data?.user) throw new ApiError({ status: 500, message: "Invalid user response" });
  return { ...data, user: normalizeUser(data.user)! };
}

export async function login(email: string, password: string, signal?: AbortSignal): Promise<AuthResponse> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail || !password) throw new ApiError({ status: 400, message: "Email and password required" });
  const data = await request<AuthResponse>("/api/auth/login", {
    method: "POST", body: { email: normalizedEmail, password }, signal,
  });
  return { ...data, user: normalizeUser(data.user) || undefined };
}

export async function register(
  email: string, password: string, username?: string, displayName?: string, signal?: AbortSignal
): Promise<AuthResponse> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail || !password) throw new ApiError({ status: 400, message: "Email and password required" });
  const body: Record<string, string> = { email: normalizedEmail, password };
  if (username) body.username = username;
  if (displayName) body.display_name = displayName;
  const data = await request<AuthResponse>("/api/auth/register", { method: "POST", body, signal });
  return { ...data, user: normalizeUser(data.user) || undefined };
}

export async function verifyEmail(email: string, code: string, signal?: AbortSignal) {
  const normalizedEmail = email.trim().toLowerCase();
  const trimmedCode = code.trim();
  if (!normalizedEmail || !trimmedCode) throw new ApiError({ status: 400, message: "Email and verification code required" });
  return request<{ status?: string; message?: string }>("/api/auth/verify-email", {
    method: "POST", body: { email: normalizedEmail, code: trimmedCode }, signal,
  });
}

export async function resendVerification(email: string, signal?: AbortSignal) {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail) throw new ApiError({ status: 400, message: "Email required" });
  return request<{ status?: string; message?: string; dev_code?: string }>("/api/auth/resend-verification", {
    method: "POST", body: { email: normalizedEmail }, signal,
  });
}

export async function forgotPassword(email: string, signal?: AbortSignal) {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail) throw new ApiError({ status: 400, message: "Email required" });
  return request<{ status?: string; message?: string; dev_code?: string }>("/api/auth/forgot-password", {
    method: "POST", body: { email: normalizedEmail }, signal,
  });
}

export async function resetPassword(email: string, code: string, newPassword: string, signal?: AbortSignal) {
  const normalizedEmail = email.trim().toLowerCase();
  const trimmedCode = code.trim();
  if (!normalizedEmail || !trimmedCode || !newPassword) throw new ApiError({ status: 400, message: "Email, code, and new password required" });
  return request<{ status?: string; message?: string }>("/api/auth/reset-password", {
    method: "POST", body: { email: normalizedEmail, code: trimmedCode, new_password: newPassword }, signal,
  });
}

export async function logout(signal?: AbortSignal) {
  try { await request<{ status?: string }>("/api/auth/logout", { method: "POST", signal }); } catch { /* ignore */ }
}

export type ConversationItem = {
  id: string;
  title?: string;
  preview?: string;
  updated_at?: string;
  created_at?: string;
};

export async function listConversations(signal?: AbortSignal): Promise<ConversationItem[]> {
  const data = await request<{ conversations?: ConversationItem[] } | ConversationItem[]>("/api/conversations", {
    method: "GET", signal,
  });
  if (Array.isArray(data)) return data;
  return data.conversations || [];
}

export async function getConversation(id: string, signal?: AbortSignal) {
  return request<{ id: string; messages?: unknown[] }>(`/api/conversations/${encodeURIComponent(id)}`, {
    method: "GET", signal,
  });
}

export async function chat(
  message: string,
  options?: { conversationId?: string; image?: { base64: string; mime?: string }; signal?: AbortSignal }
): Promise<ChatResponse> {
  const trimmed = (message || "").trim();
  const image = options?.image;
  const hasImage = Boolean(image?.base64);
  if (!trimmed && !hasImage) throw new ApiError({ status: 400, message: "Message required" });
  if (trimmed.length > 16000) throw new ApiError({ status: 400, message: "Message too long" });
  const body: Record<string, unknown> = { message: trimmed || "What do you see in this image?" };
  if (options?.conversationId) body.conversation_id = options.conversationId;
  if (hasImage) {
    body.image_base64 = image!.base64;
    body.image_mime = image!.mime || "image/jpeg";
  }
  return request<ChatResponse>("/api/chat", { method: "POST", body, signal: options?.signal });
}

export async function healthCheck() {
  return request<{ status?: string }>("/health", { method: "GET" });
}

export async function createCheckoutSession(
  plan: string,
  signal?: AbortSignal,
  provider?: "paystack" | "stripe" | "stars" | string,
) {
  const body: Record<string, string> = { plan };
  if (provider) body.provider = provider;
  return request<{
    status: string; url?: string; checkout_url?: string; session_id?: string;
    provider?: string; access_code?: string; public_key?: string; stars?: number; message?: string;
  }>("/api/billing/create-checkout-session", { method: "POST", body, signal });
}

export async function getBillingConfig(signal?: AbortSignal) {
  return request<{ status?: string; provider?: string; currency?: string; configured?: boolean; methods?: string[]; plans?: Record<string, unknown> }>("/api/billing/config", { method: "GET", signal });
}

export type AdminStats = Record<string, unknown>;
export type AdminMe = Record<string, unknown>;

export async function getAdminStats(signal?: AbortSignal): Promise<AdminStats> {
  return request<AdminStats>("/api/admin/stats", { method: "GET", signal });
}
export async function getAdminMe(signal?: AbortSignal): Promise<AdminMe> {
  return request<AdminMe>("/api/admin/me", { method: "GET", signal });
}
export async function adminUnlock(password: string, signal?: AbortSignal) {
  return request<{ status?: string }>("/api/admin/unlock", { method: "POST", body: { password }, signal });
}
export async function adminListUsers(signal?: AbortSignal) {
  return request<{ users?: unknown[] }>("/api/admin/users", { method: "GET", signal });
}
export async function adminBanUser(userId: string, reason?: string, signal?: AbortSignal) {
  return request<{ status?: string }>("/api/admin/users/ban", { method: "POST", body: { user_id: userId, reason: reason || "" }, signal });
}
export async function adminUnbanUser(userId: string, signal?: AbortSignal) {
  return request<{ status?: string }>("/api/admin/users/unban", { method: "POST", body: { user_id: userId }, signal });
}

export async function ttsSpeak(text: string, options?: { voice?: string; signal?: AbortSignal }): Promise<{ audio_base64?: string; mime?: string; url?: string }> {
  return request("/api/tts", { method: "POST", body: { text, voice: options?.voice }, signal: options?.signal });
}

export type MarketSnapshot = {
  symbol?: string; price?: number; change?: number; signal?: string; trend?: string;
  [key: string]: unknown;
};

export async function getMarkets(signal?: AbortSignal) {
  return request<{ symbols?: MarketSnapshot[] }>("/api/markets", { method: "GET", signal });
}
export async function getMarketDetail(symbol: string, signal?: AbortSignal) {
  return request<Record<string, unknown>>(`/api/markets/${encodeURIComponent(symbol)}`, { method: "GET", signal });
}
export async function getSignals(signal?: AbortSignal) {
  return request<{ signals?: MarketSnapshot[] }>("/api/signals", { method: "GET", signal });
}
export async function getNews(signal?: AbortSignal) {
  return request<{
    items?: unknown[];
    assets?: unknown[];
    global_headlines?: unknown[];
    status?: string;
  }>("/api/news", { method: "GET", signal });
}

export type AgentBrief = { summary_text?: string; [key: string]: unknown };
export type AgentJob = { id?: string; status?: string; [key: string]: unknown };

export async function getAgentStatus(signal?: AbortSignal) {
  return request<Record<string, unknown>>("/api/agent/status", { method: "GET", signal });
}
export async function runAgentGoal(goal: string, signal?: AbortSignal) {
  return request<Record<string, unknown>>("/api/agent/run", { method: "POST", body: { goal }, signal });
}
export async function generateMorningBrief(signal?: AbortSignal) {
  return request<{ brief?: AgentBrief }>("/api/agent/morning-brief", { method: "POST", signal });
}
export async function getLatestMorningBrief(signal?: AbortSignal) {
  return request<{ brief?: AgentBrief | null; status?: string }>("/api/agent/morning-brief/latest", { method: "GET", signal });
}
export async function listAgentJobs(signal?: AbortSignal) {
  return request<{ jobs?: AgentJob[] }>("/api/agent/jobs", { method: "GET", signal });
}
export async function approveAgentJob(jobId: string, signal?: AbortSignal) {
  return request<{ status?: string; job?: AgentJob }>("/api/agent/jobs/approve", { method: "POST", body: { job_id: jobId }, signal });
}
export async function getAgentLearning(signal?: AbortSignal) {
  return request<{ learning?: Record<string, unknown>[] }>("/api/agent/learning", { method: "GET", signal });
}
export async function getAgentV2(signal?: AbortSignal) {
  return request<Record<string, unknown>>("/api/agent/v2", { method: "GET", signal });
}
export async function getAgentIntelligence(signal?: AbortSignal) {
  return request<Record<string, unknown>>("/api/agent/intelligence", { method: "GET", signal });
}
export async function getAgentPreferences(signal?: AbortSignal) {
  return request<{ preferences?: Record<string, unknown> }>("/api/agent/preferences", { method: "GET", signal });
}
export async function updateAgentPreferences(preferences: Record<string, unknown>, signal?: AbortSignal) {
  return request<{ status?: string }>("/api/agent/preferences", { method: "POST", body: preferences, signal });
}
export async function getAgentActionStatus(signal?: AbortSignal) {
  return request<Record<string, unknown>>("/api/agent/actions/status", { method: "GET", signal });
}
export async function listAgentActions(signal?: AbortSignal) {
  return request<{ actions?: Record<string, unknown>[] }>("/api/agent/actions", { method: "GET", signal });
}
export async function approveAgentAction(actionId: string, signal?: AbortSignal) {
  return request<{ status?: string }>("/api/agent/actions/approve", { method: "POST", body: { action_id: actionId }, signal });
}

export const api = {
  getBaseUrl, getMe, login, register, verifyEmail, resendVerification, forgotPassword, resetPassword, logout,
  listConversations, getConversation, chat, healthCheck, createCheckoutSession, getBillingConfig,
  getAdminStats, getAdminMe, adminUnlock, adminListUsers, adminBanUser, adminUnbanUser, ttsSpeak,
  getMarkets, getMarketDetail, getSignals, getNews,
  getAgentStatus, runAgentGoal, generateMorningBrief, getLatestMorningBrief, listAgentJobs, approveAgentJob,
  getAgentLearning, getAgentV2, getAgentIntelligence, getAgentPreferences, updateAgentPreferences,
  getAgentActionStatus, listAgentActions, approveAgentAction,
};

export type { AuthUser, AuthResponse, MeResponse, ChatResponse, ApiErrorData } from "@/types";
