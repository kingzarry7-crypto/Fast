// ==========================================================================
// AUTH
// ==========================================================================
export interface AuthUser {
  id: string;
  email: string;
  username?: string | null;
  display_name?: string | null;
  account_status?: string | null;
  created_at?: string | null;
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

// ==========================================================================
// CHAT
// ==========================================================================
export interface ChatResponse {
  status: string;
  reply: string;
  conversation_id: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  timestamp: string;
  status?: string;
  capability?: string;
}

// ==========================================================================
// API ERROR
// ==========================================================================
export interface ApiErrorData {
  status: number;
  message: string;
  detail?: string;
  raw?: unknown;
}
