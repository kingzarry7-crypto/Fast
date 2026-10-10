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

// Backward-compatible alias used by AppProviders. Keep getMe() as the canonical implementation.
export async function getCurrentUser(signal?: AbortSignal): Promise<AuthUser | null> {
  const data = await getMe(signal);
  return data.user;
}

export async function login(email: string, password: string, signal?: AbortSignal): Promise<AuthResponse> {
  const normalizedEmail = email.trim().toLowerCase();
  if (!normalizedEmail || !password) throw new ApiError({ status: 400, message: "Email and password required" });
  const data = await request<AuthResponse>("/api/auth/login", {
    method: "POST", body: { email: normalizedEmail, password }, signal,
  });
  return { ...data, user: normalizeUser(data.user) };
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
  return { ...data, user: normalizeUser(data.user) };
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

export async function createConversation(title?: string, signal?: AbortSignal): Promise<ConversationItem> {
  const data = await request<{
    status?: string;
    conversation?: ConversationItem;
    id?: string;
    title?: string;
    preview?: string;
    updated_at?: string;
    created_at?: string;
  }>("/api/conversations", {
    method: "POST",
    body: title ? { title } : {},
    signal,
  });
  const conv = data.conversation || data;
  if (conv && conv.id) {
    return {
      id: String(conv.id),
      title: conv.title != null ? String(conv.title) : undefined,
      preview: conv.preview != null ? String(conv.preview) : undefined,
      updated_at: conv.updated_at != null ? String(conv.updated_at) : undefined,
      created_at: conv.created_at != null ? String(conv.created_at) : undefined,
    };
  }
  throw new ApiError({ status: 500, message: "Invalid create conversation response" });
}

export type ConversationMessage = {
  id?: string;
  role?: string;
  content?: string;
  created_at?: string;
};

export async function getConversationMessages(
  id: string,
  signal?: AbortSignal
): Promise<ConversationMessage[]> {
  const data = await request<{
    status?: string;
    conversation_id?: string;
    messages?: ConversationMessage[];
  }>(`/api/conversations/${encodeURIComponent(id)}/messages`, {
    method: "GET",
    signal,
  });
  return Array.isArray(data.messages) ? data.messages : [];
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

// Backward-compatible chat method used by the existing useChat hook.
export async function sendChatMessage(
  message: string,
  image?: { base64: string; mime?: string },
  signal?: AbortSignal,
  conversationId?: string
): Promise<ChatResponse> {
  return chat(message, {
    image,
    signal,
    conversationId,
  });
}

export async function streamChatMessage(
  message: string,
  options: {
    conversationId?: string;
    signal?: AbortSignal;
    onDelta: (text: string) => void;
    onStart?: (provider?: string) => void;
    onActivity?: (activity: { stage?: string; label: string; done: boolean; searches?: number; sources?: number }) => void;
    onAgent?: (agent: { id?: string; status?: string; activity?: string }) => void;
  }
): Promise<{ reply: string; conversation_id?: string; approval?: { id: string; provider: "google"; operation: string; target?: string }; agent?: { id?: string; status?: string; activity?: string } }> {
  const trimmed = (message || "").trim();
  if (!trimmed) throw new ApiError({ status: 400, message: "Message required" });
  if (trimmed.length > 4000) throw new ApiError({ status: 400, message: "Message too long" });

  const response = await fetch(buildUrl("/api/chat/stream"), {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify({
      message: trimmed,
      ...(options.conversationId ? { conversation_id: options.conversationId } : {}),
    }),
    signal: options.signal,
  });

  if (!response.ok) {
    let message = response.statusText || `HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (data && typeof data.detail === "string") message = data.detail;
    } catch { /* non-JSON response */ }
    throw new ApiError({ status: response.status, message });
  }

  if (!response.body) throw new ApiError({ status: 502, message: "Streaming response unavailable" });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let reply = "";
  let conversationId: string | undefined;
  let streamError = "";
  let approval: { id: string; provider: "google"; operation: string; target?: string } | undefined;
  let agent: { id?: string; status?: string; activity?: string } | undefined;

  const consumeEvent = (raw: string) => {
    const line = raw.split(/\r?\n/).find((value) => value.startsWith("data:"));
    if (!line) return;
    try {
      const event = JSON.parse(line.slice(5).trim()) as Record<string, unknown>;
      if (event.type === "start") {
        options.onStart?.(typeof event.provider === "string" ? event.provider : undefined);
      } else if (event.type === "activity" && typeof event.label === "string") {
        options.onActivity?.({
          stage: typeof event.stage === "string" ? event.stage : undefined,
          label: event.label,
          done: event.done === true,
          searches: typeof event.searches === "number" ? event.searches : undefined,
          sources: typeof event.sources === "number" ? event.sources : undefined,
        });
      } else if (event.type === "agent" && event.agent && typeof event.agent === "object") {
        const value = event.agent as Record<string, unknown>;
        agent = {
          id: typeof value.id === "string" ? value.id : undefined,
          status: typeof value.status === "string" ? value.status : undefined,
          activity: typeof value.activity === "string" ? value.activity : undefined,
        };
        options.onAgent?.(agent);
      } else if (event.type === "delta" && typeof event.text === "string") {
        reply += event.text;
        options.onDelta(event.text);
      } else if (event.type === "done") {
        if (typeof event.conversation_id === "string") conversationId = event.conversation_id;
        if (typeof event.text === "string" && event.text) reply = event.text;
        if (typeof event.approval_id === "string" && event.approval_id && event.provider === "google") {
          approval = { id: event.approval_id, provider: "google", operation: typeof event.operation === "string" ? event.operation : "send_gmail", target: typeof event.target === "string" ? event.target : undefined };
        }
      } else if (event.type === "error") {
        streamError = typeof event.message === "string" ? event.message : "Streaming failed";
      }
    } catch {
      // Ignore malformed SSE frames; the final fallback/error frame handles failure.
    }
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() || "";
      for (const frame of frames) consumeEvent(frame);
    }
    buffer += decoder.decode();
    if (buffer.trim()) consumeEvent(buffer);
  } finally {
    reader.releaseLock();
  }

  if (streamError) throw new ApiError({ status: 502, message: streamError });
  if (!reply.trim()) throw new ApiError({ status: 502, message: "AI streaming returned no response" });
  return { reply, conversation_id: conversationId, approval, agent };
}

export async function decideGoogleApproval(
  approvalId: string,
  decision: "once" | "always" | "reject",
  signal?: AbortSignal,
): Promise<{ status?: string; approval_id?: string; verified?: boolean; permission_saved?: boolean; result?: unknown }> {
  return request<{ status?: string; approval_id?: string; verified?: boolean; permission_saved?: boolean; result?: unknown }>(
    `/api/connectors/google/approve/${encodeURIComponent(approvalId)}`,
    { method: "POST", body: { approved: decision !== "reject", remember: decision === "always" }, signal },
  );
}

export async function generateChatSuggestions(
  userMessage: string,
  assistantResponse: string,
  signal?: AbortSignal,
): Promise<{ status?: string; suggestions: string[] }> {
  return request<{ status?: string; suggestions: string[] }>(
    "/api/chat/suggestions",
    {
      method: "POST",
      body: {
        user_message: userMessage,
        assistant_response: assistantResponse,
      },
      signal,
    },
  );
}

export async function healthCheck() {
  return request<{ status?: string }>("/health", { method: "GET" });
}

export async function getRealtimeStatus(signal?: AbortSignal) {
  return request<{ status?: string; enabled?: boolean; model?: string | null }>(
    "/api/realtime/status",
    { method: "GET", signal }
  );
}

export async function startRealtimeCall(
  sdpOffer: string,
  conversationId?: string | null,
  signal?: AbortSignal
): Promise<string> {
  const path = conversationId
    ? `/api/realtime/call?conversation_id=${encodeURIComponent(conversationId)}`
    : "/api/realtime/call";
  const response = await fetch(buildUrl(path), {
    method: "POST",
    headers: {
      Accept: "application/sdp",
      "Content-Type": "application/sdp",
    },
    credentials: "include",
    body: sdpOffer,
    signal,
  });
  if (!response.ok) {
    let message = response.statusText || `HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (data && typeof data.detail === "string") message = data.detail;
    } catch { /* non-JSON error */ }
    throw new ApiError({ status: response.status, message });
  }
  return response.text();
}

export async function saveRealtimeTranscript(
  conversationId: string | null | undefined,
  role: "user" | "assistant",
  content: string,
  signal?: AbortSignal
) {
  return request<{ status?: string; conversation_id?: string | null; message_id?: string | null }>(
    "/api/realtime/transcript",
    {
      method: "POST",
      body: { conversation_id: conversationId || null, role, content },
      signal,
    }
  );
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

export async function adminEmailBroadcast(
  payload: { subject: string; message: string; audience?: string; html?: string },
  signal?: AbortSignal
) {
  return request<{
    status?: string;
    sent?: number;
    failed?: number;
    total?: number;
    audience?: string;
    message?: string;
    from?: string;
  }>("/api/admin/email-broadcast", {
    method: "POST",
    body: {
      subject: payload.subject,
      message: payload.message,
      audience: payload.audience || "active",
      html: payload.html,
    },
    signal,
  });
}

export type TtsVoice = "bella" | "male";

export async function synthesizeSpeech(
  text: string,
  style: string = "human",
  signal?: AbortSignal,
  voice: TtsVoice = "bella"
): Promise<Blob> {
  const response = await fetch(buildUrl("/api/tts"), {
    method: "POST",
    headers: {
      Accept: "audio/mpeg",
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify({ text, style, voice }),
    signal,
  });
  if (!response.ok) {
    let message = response.statusText || `HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (data && typeof data.detail === "string") message = data.detail;
    } catch { /* non-JSON error */ }
    throw new ApiError({ status: response.status, message });
  }
  return response.blob();
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
  return request<{
    signals?: MarketSnapshot[];
    actionable_count?: number;
    status?: string;
  }>("/api/signals", { method: "GET", signal });
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

export type PlatformStatus = {
  status?: string;
  telegram?: {
    configured?: boolean;
    reachable?: boolean;
    username?: string | null;
    url?: string | null;
  };
  discord?: {
    configured?: boolean;
    reachable?: boolean;
    username?: string | null;
    invite_url?: string | null;
  };
};

export async function getPlatformStatus(signal?: AbortSignal): Promise<PlatformStatus> {
  return request<PlatformStatus>("/api/platforms/status", {
    method: "GET",
    signal,
  });
}

export type ChatBehaviorPreferences = {
  signalsOnly: boolean;
  humanReplies: boolean;
  rememberPreferences: boolean;
  riskReminder: boolean;
};

export async function getChatBehaviorPreferences(
  signal?: AbortSignal
): Promise<{ status?: string; preferences: ChatBehaviorPreferences }> {
  return request<{ status?: string; preferences: ChatBehaviorPreferences }>(
    "/api/settings/preferences",
    { method: "GET", signal }
  );
}

export async function saveChatBehaviorPreferences(
  preferences: ChatBehaviorPreferences,
  signal?: AbortSignal
): Promise<{ status?: string; preferences: ChatBehaviorPreferences }> {
  return request<{ status?: string; preferences: ChatBehaviorPreferences }>(
    "/api/settings/preferences",
    { method: "POST", body: preferences, signal }
  );
}

export async function createMemoryLinkCode(signal?: AbortSignal) {
  return request<{ status?: string; code: string; expires_in_minutes: number; instructions?: string }>(
    "/api/memory/link-code",
    { method: "POST", signal }
  );
}

export const api = {
  getBaseUrl, getMe, getCurrentUser, login, register, verifyEmail, resendVerification, forgotPassword, resetPassword, logout,
  listConversations, createConversation, getConversation, getConversationMessages, chat, sendChatMessage, streamChatMessage, decideGoogleApproval, generateChatSuggestions, healthCheck,
  getRealtimeStatus, startRealtimeCall, saveRealtimeTranscript, getPlatformStatus, getChatBehaviorPreferences, saveChatBehaviorPreferences, createMemoryLinkCode, createCheckoutSession, getBillingConfig,
  getAdminStats, getAdminMe, adminUnlock, adminListUsers, adminBanUser, adminUnbanUser, adminEmailBroadcast, ttsSpeak, synthesizeSpeech,
  getMarkets, getMarketDetail, getSignals, getNews,
  getAgentStatus, runAgentGoal, generateMorningBrief, getLatestMorningBrief, listAgentJobs, approveAgentJob,
  getAgentLearning, getAgentV2, getAgentIntelligence, getAgentPreferences, updateAgentPreferences,
  getAgentActionStatus, listAgentActions, approveAgentAction, getKZAgentStatus,
};

export type { AuthUser, AuthResponse, MeResponse, ChatResponse, ApiErrorData } from "@/types";


export async function getKZAgentStatus(
  workflowId: string,
  signal?: AbortSignal,
): Promise<{ status?: string; agent?: { id?: string; goal?: string; status?: string; activity?: string; completed_steps?: number; total_steps?: number; current_step?: { title?: string; status?: string; approval_id?: string }; requires_approval?: boolean } }> {
  return request<{ status?: string; agent?: { id?: string; goal?: string; status?: string; activity?: string; completed_steps?: number; total_steps?: number; current_step?: { title?: string; status?: string; approval_id?: string }; requires_approval?: boolean } }>(
    `/api/agent/status/${encodeURIComponent(workflowId)}`,
    { method: "GET", signal },
  );
}
