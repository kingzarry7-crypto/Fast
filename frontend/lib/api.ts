// Fast/frontend/lib/api.ts
// Production API client for KING ZARRY AI web frontend
// Only exposes endpoints confirmed in api.py.
// No market/signal invention and no Telegram integration.

function getBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!raw) {
    return "";
  }

  return raw.trim().replace(/\/+$/, "");
}

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const base = getBaseUrl();

  return base ? `${base}${normalizedPath}` : normalizedPath;
}

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface AuthUser {
  id: string;
  email: string;
  username?: string | null;
  display_name?: string | null;
  account_status?: string | null;
  created_at?: string | null;
}

export interface ApiErrorData {
  status: number;
  message: string;
  detail?: string;
  raw?: unknown;
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

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

export interface AuthResponse {
  status: string;
  message?: string;
  user?: AuthUser;
}

export interface MeResponse {
  status: string;
  user: AuthUser;
}

export interface LogoutResponse {
  status: string;
  message?: string;
}

export interface ChatResponse {
  status: string;
  reply: string;
  conversation_id: string;
}

// -----------------------------------------------------------------------------
// Error parsing
// -----------------------------------------------------------------------------

interface ParsedError {
  message: string;
  detail?: string;
  raw?: unknown;
}

async function parseErrorBody(res: Response): Promise<ParsedError> {
  try {
    const text = await res.text();

    if (!text) {
      return {
        message: `Request failed (${res.status})`,
      };
    }

    try {
      const json: unknown = JSON.parse(text);

      if (
        json !== null &&
        typeof json === "object" &&
        !Array.isArray(json)
      ) {
        const data = json as Record<string, unknown>;

        const message =
          (typeof data.detail === "string" && data.detail) ||
          (typeof data.message === "string" && data.message) ||
          (typeof data.error === "string" && data.error) ||
          `Request failed (${res.status})`;

        return {
          message,
          detail:
            typeof data.detail === "string"
              ? data.detail
              : undefined,
          raw: data,
        };
      }

      return {
        message: `Request failed (${res.status})`,
        raw: json,
      };
    } catch {
      return {
        message:
          text.slice(0, 500) ||
          `Request failed (${res.status})`,
        raw: text,
      };
    }
  } catch {
    return {
      message: `Request failed (${res.status})`,
    };
  }
}

// -----------------------------------------------------------------------------
// Core request helper
// -----------------------------------------------------------------------------

async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const {
    method = "GET",
    body,
    signal,
    headers = {},
  } = options;

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
      throw new ApiError({
        status: 400,
        message: "Invalid request body",
      });
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
    if (
      error instanceof DOMException &&
      error.name === "AbortError"
    ) {
      throw error;
    }

    if (
      error !== null &&
      typeof error === "object" &&
      "name" in error &&
      error.name === "AbortError"
    ) {
      throw error;
    }

    const message =
      error instanceof Error
        ? error.message
        : "Network error";

    throw new ApiError({
      status: 0,
      message,
      raw: error,
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    const error = await parseErrorBody(response);

    throw new ApiError({
      status: response.status,
      message: error.message,
      detail: error.detail,
      raw: error.raw,
    });
  }

  const text = await response.text();

  if (!text) {
    return undefined as T;
  }

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

// -----------------------------------------------------------------------------
// Authentication
// -----------------------------------------------------------------------------

async function getCurrentUser(
  signal?: AbortSignal
): Promise<AuthUser> {
  const data = await request<MeResponse>(
    "/api/auth/me",
    {
      method: "GET",
      signal,
    }
  );

  if (!data?.user) {
    throw new ApiError({
      status: 500,
      message: "Invalid user response",
    });
  }

  return data.user;
}

async function login(
  email: string,
  password: string,
  signal?: AbortSignal
): Promise<AuthResponse> {
  const normalizedEmail = email.trim().toLowerCase();

  if (!normalizedEmail || !password) {
    throw new ApiError({
      status: 400,
      message: "Email and password required",
    });
  }

  return request<AuthResponse>(
    "/api/auth/login",
    {
      method: "POST",
      body: {
        email: normalizedEmail,
        password,
      },
      signal,
    }
  );
}

async function register(
  email: string,
  password: string,
  username?: string,
  displayName?: string,
  signal?: AbortSignal
): Promise<AuthResponse> {
  const normalizedEmail = email.trim().toLowerCase();

  if (!normalizedEmail || !password) {
    throw new ApiError({
      status: 400,
      message: "Email and password required",
    });
  }

  const payload: Record<string, unknown> = {
    email: normalizedEmail,
    password,
  };

  const normalizedUsername = username?.trim();
  const normalizedDisplayName = displayName?.trim();

  if (normalizedUsername) {
    payload.username = normalizedUsername;
  }

  if (normalizedDisplayName) {
    payload.display_name = normalizedDisplayName;
  }

  return request<AuthResponse>(
    "/api/auth/register",
    {
      method: "POST",
      body: payload,
      signal,
    }
  );
}

async function logout(
  signal?: AbortSignal
): Promise<LogoutResponse> {
  return request<LogoutResponse>(
    "/api/auth/logout",
    {
      method: "POST",
      signal,
    }
  );
}

// -----------------------------------------------------------------------------
// Chat
// -----------------------------------------------------------------------------

async function sendChatMessage(
  message: string,
  signal?: AbortSignal
): Promise<ChatResponse> {
  const trimmed = message.trim();

  if (!trimmed) {
    throw new ApiError({
      status: 400,
      message: "Message required",
    });
  }

  if (trimmed.length > 4000) {
    throw new ApiError({
      status: 400,
      message: "Message too long",
    });
  }

  const data = await request<ChatResponse>(
    "/api/chat",
    {
      method: "POST",
      body: {
        message: trimmed,
      },
      signal,
    }
  );

  if (!data?.reply) {
    throw new ApiError({
      status: 500,
      message: "Invalid chat response",
    });
  }

  return data;
}

// -----------------------------------------------------------------------------
// Exported API client
// -----------------------------------------------------------------------------

export const api = {
  // Base URL helpers
  buildUrl,
  getBaseUrl,

  // Authentication
  getCurrentUser,
  me: getCurrentUser,
  fetchMe: getCurrentUser,
  getMe: getCurrentUser,
  login,
  register,
  logout,

  // Chat
  sendChatMessage,
  sendMessage: sendChatMessage,
  chat: sendChatMessage,
};

export default api;
