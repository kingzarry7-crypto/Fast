// Fast/frontend/types/index.ts
// Central type barrel for KING ZARRY AI.

export type {
  AuthUser,
  AccountStatus,
  LoginInput,
  RegisterInput,
  AuthResponse,
  MeResponse,
  LogoutResponse,
  AuthState,
} from "./auth";

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
  activitySteps?: Array<{ label: string; done: boolean }>;
  webSources?: Array<{ title: string; url: string }>;
  capability?: string;
  suggestions?: string[];
  imagePreviewUrl?: string;
  imageName?: string;
  approval?: { id: string; provider: "google"; operation: string; target?: string; allowAlways?: boolean };
}

export interface ApiErrorData {
  status: number;
  message: string;
  detail?: string;
  raw?: unknown;
}
