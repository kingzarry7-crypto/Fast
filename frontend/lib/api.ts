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
  const data = await request<MeResponse>("/api/auth/me", { method: "GET", signal });
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
  if (username?.trim()) payload.username = username.trim();
  if (displayName?.trim()) payload.display_name = displayName.trim();
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
  if (newPassword.length < 8) throw new ApiError({ status: 400, message: "Password must be at least 8 characters" });
  return request<{ status: string; message?: string }>("/api/auth/reset-password", {
    method: "POST",
    body: { email: normalizedEmail, code: trimmedCode, new_password: newPassword },
    signal,
  });
}

export async function logout(signal?: AbortSignal) {
  return request<{ status: string; message?: string }>("/api/auth/logout", { method: "POST", signal });
}

export interface SendImagePayload { base64: string; mime: string; }

export async function sendChatMessage(
  message: string,
  image?: SendImagePayload,
  signal?: AbortSignal,
  conversationId?: string | null
): Promise<ChatResponse> {
  const trimmed = message.trim();
  const hasImage = !!(image && image.base64);
  if (!trimmed && !hasImage) throw new ApiError({ status: 400, message: "Message required" });
  if (trimmed.length > 4000) throw new ApiError({ status: 400, message: "Message too long" });
  const body: Record<string, unknown> = { message: trimmed || "What do you see in this image?" };
  if (conversationId) body.conversation_id = conversationId;
  if (hasImage) {
    body.image_base64 = image!.base64;
    body.image_mime = image!.mime || "image/jpeg";
  }
  const data = await request<ChatResponse>("/api/chat", { method: "POST", body, signal });
  if (!data?.reply) throw new ApiError({ status: 500, message: "Invalid chat response" });
  return data;
}

export async function healthCheck() {
  return request<{ status: string; database?: { status: string } }>("/health", { method: "GET" });
}

export async function createCheckoutSession(plan: string, signal?: AbortSignal) {
  return request<{ status: string; checkout_url: string; session_id?: string }>("/api/billing/create-checkout-session", {
    method: "POST",
    body: { plan },
    signal,
  });
}

export interface AdminUserItem {
  id?: string;
  email?: string;
  username?: string;
  account_status?: string;
  created_at?: string;
  last_login_at?: string;
}

export interface AdminStats {
  status: string;
  admin_email?: string;
  users_total?: number;
  users_active_7d?: number;
  users_active_30d?: number;
  users_new_7d?: number;
  sessions_active?: number;
  conversations_total?: number;
  messages_total?: number;
  messages_24h?: number;
  active_subscribers: number;
  payments_count: number;
  revenue_cents: number;
  revenue_usd: number;
  recent_users?: AdminUserItem[];
  recent_payments: Array<{ email?: string; plan?: string; amount_cents?: number; status?: string; created_at?: string }>;
  note?: string;
}

export async function getAdminStats(signal?: AbortSignal): Promise<AdminStats> {
  return request("/api/admin/stats", { method: "GET", signal });
}

export interface AdminMe {
  status: string;
  is_admin: boolean;
  email?: string;
  requires_password?: boolean;
  admin_emails_configured?: boolean;
  admin_email_count?: number;
  hint?: string | null;
}

export async function getAdminMe(signal?: AbortSignal): Promise<AdminMe> {
  return request("/api/admin/me", { method: "GET", signal });
}

export async function unlockAdmin(password: string, signal?: AbortSignal) {
  return request<{ status: string; message?: string }>("/api/admin/unlock", { method: "POST", body: { password }, signal });
}

export async function setAdminUserStatus(
  userId: string,
  status: "active" | "suspended" | "banned",
  signal?: AbortSignal
) {
  return request<{ status: string; user: AdminUserItem }>(`/api/admin/users/${encodeURIComponent(userId)}/status`, {
    method: "POST",
    body: { status },
    signal,
  });
}

export async function updateUserStatus(
  userId: string,
  status: "active" | "suspended" | "banned",
  signal?: AbortSignal
) {
  return setAdminUserStatus(userId, status, signal);
}

export async function listAdminUsers(limit = 50, signal?: AbortSignal) {
  return request<{ status: string; users: AdminUserItem[] }>(`/api/admin/users?limit=${limit}`, { method: "GET", signal });
}

export interface ConversationItem {
  id: string;
  title: string;
  preview?: string;
  created_at?: string;
  updated_at?: string;
}

export async function listConversations(signal?: AbortSignal): Promise<ConversationItem[]> {
  const data = await request<{ status: string; conversations: ConversationItem[] }>("/api/conversations", { method: "GET", signal });
  return data?.conversations || [];
}

export async function createConversation(signal?: AbortSignal): Promise<ConversationItem> {
  const data = await request<{ status: string; conversation: ConversationItem }>("/api/conversations", { method: "POST", signal });
  if (!data?.conversation?.id) throw new ApiError({ status: 500, message: "Could not create conversation" });
  return data.conversation;
}

export async function getConversationMessages(conversationId: string, signal?: AbortSignal) {
  const data = await request<{ status: string; messages: { role: string; content: string; created_at?: string; id?: string }[] }>(
    `/api/conversations/${encodeURIComponent(conversationId)}/messages`,
    { method: "GET", signal }
  );
  return data?.messages || [];
}

export type TtsVoice = "bella" | "male";

export async function synthesizeSpeech(
  text: string,
  style: "slow" | "normal" | "human" | "fast" = "human",
  signal?: AbortSignal,
  voice: TtsVoice = "bella"
): Promise<Blob> {
  const trimmed = text.trim();
  if (!trimmed) throw new ApiError({ status: 400, message: "Text required" });
  const url = buildUrl("/api/tts");
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { Accept: "audio/mpeg", "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ text: trimmed.slice(0, 2000), style, voice: voice === "male" ? "male" : "bella" }),
      signal,
    });
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError({ status: 0, message: error instanceof Error ? error.message : "Network error" });
  }
  if (!response.ok) {
    let message = `TTS failed (${response.status})`;
    try {
      const j = await response.json();
      if (j?.detail) message = String(j.detail);
    } catch { /* ignore */ }
    throw new ApiError({ status: response.status, message });
  }
  return response.blob();
}

export interface AgentJob {
  id: string;
  user_id?: string | null;
  job_type: string;
  title: string;
  payload_json?: string | null;
  status: string;
  needs_approval?: number;
  approved_at?: string | null;
  result_json?: string | null;
  error?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AgentBrief {
  id?: string;
  trading_date?: string;
  generated_at?: string;
  summary_text?: string;
  actionable_count?: number;
  assets?: Array<Record<string, unknown>>;
  disclaimer?: string;
}

export async function getAgentStatus(signal?: AbortSignal) {
  return request<Record<string, unknown>>("/api/agent/status", { method: "GET", signal });
}

export async function runAgentGoal(goal: string, signal?: AbortSignal) {
  const trimmed = goal.trim();
  if (!trimmed) throw new ApiError({ status: 400, message: "Goal required" });
  return request<Record<string, unknown>>("/api/agent/run", { method: "POST", body: { goal: trimmed.slice(0, 2000) }, signal });
}

export async function generateMorningBrief(signal?: AbortSignal) {
  return request<{ status: string; brief?: AgentBrief }>("/api/agent/morning-brief", { method: "POST", signal });
}

export async function getLatestMorningBrief(signal?: AbortSignal) {
  return request<{ status: string; brief?: AgentBrief | null }>("/api/agent/morning-brief/latest", { method: "GET", signal });
}

export async function listAgentJobs(signal?: AbortSignal) {
  return request<{ status: string; jobs: AgentJob[] }>("/api/agent/jobs", { method: "GET", signal });
}

export async function approveAgentJob(jobId: string, signal?: AbortSignal) {
  return request<{ status: string; job?: AgentJob }>("/api/agent/jobs/approve", { method: "POST", body: { job_id: jobId }, signal });
}

export async function getAgentLearning(signal?: AbortSignal) {
  return request<{ status: string; learning: Record<string, unknown>[] }>("/api/agent/learning", { method: "GET", signal });
}

export interface MarketSnapshot {
  symbol: string;
  timeframe?: string;
  price?: number | string | null;
  signal?: string;
  trend?: string;
  confidence?: string | number;
  strength?: string | number;
  rsi?: number;
  support?: number;
  resistance?: number;
  entry?: string | number;
  stop_loss?: string | number;
  tp1?: string | number;
  tp2?: string | number;
  tp3?: string | number;
  reasons?: string[];
  news?: Record<string, unknown>;
  error?: string;
  mtf?: unknown;
  structure?: unknown;
  volatility?: unknown;
}

export async function getMarkets(signal?: AbortSignal) {
  return request<{ status: string; symbols: MarketSnapshot[]; count?: number }>("/api/markets", { method: "GET", signal });
}

export async function getMarketDetail(symbol: string, timeframe = "15m", signal?: AbortSignal) {
  const sym = encodeURIComponent(symbol);
  return request<{ status: string; market: MarketSnapshot }>(`/api/markets/${sym}?timeframe=${encodeURIComponent(timeframe)}`, {
    method: "GET",
    signal,
  });
}

export async function getSignals(signal?: AbortSignal) {
  return request<{ status: string; signals: MarketSnapshot[]; actionable_count?: number; disclaimer?: string }>("/api/signals", {
    method: "GET",
    signal,
  });
}

export async function getNews(signal?: AbortSignal) {
  return request<{ status: string; assets: Array<Record<string, unknown>>; global_headlines?: unknown[]; disclaimer?: string }>("/api/news", {
    method: "GET",
    signal,
  });
}

export const api = {
  buildUrl,
  getBaseUrl,
  getCurrentUser,
  me: getCurrentUser,
  login,
  register,
  verifyEmail,
  resendVerificationCode,
  forgotPassword,
  resetPassword,
  logout,
  sendChatMessage,
  healthCheck,
  createCheckoutSession,
  getAdminStats,
  getAdminMe,
  unlockAdmin,
  setAdminUserStatus,
  updateUserStatus,
  listAdminUsers,
  listConversations,
  createConversation,
  getConversationMessages,
  synthesizeSpeech,
  getAgentStatus,
  runAgentGoal,
  generateMorningBrief,
  getLatestMorningBrief,
  listAgentJobs,
  approveAgentJob,
  getAgentLearning,
  getMarkets,
  getMarketDetail,
  getSignals,
  getNews,
};

export type { AuthUser, AuthResponse, MeResponse, ChatResponse, ApiErrorData } from "@/types";
