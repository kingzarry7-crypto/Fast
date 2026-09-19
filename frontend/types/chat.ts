// Fast/frontend/types/chat.ts
// Chat data contracts for KING ZARRY AI web frontend.
// Types only. No logic, React, API calls, or side effects.

/**
 * Role of a chat message.
 */
export type ChatRole =
  | "user"
  | "assistant";

/**
 * Primary chat message.
 *
 * id is a frontend message identifier and is not
 * an authentication or security token.
 */
export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  created_at?: string | null;
  conversation_id?: string | null;
  error?: string | null;
}

/**
 * Payload used to send a chat message.
 *
 * The backend owns AI model and provider configuration.
 */
export interface SendMessageInput {
  message: string;
}

/**
 * Compatibility alias for existing imports.
 */
export type ChatInput = SendMessageInput;

/**
 * Response returned by the web chat endpoint.
 */
export interface ChatResponse {
  reply: string;
  conversation_id?: string | null;
  status?: string;
}

/**
 * Minimal conversation contract for frontend use.
 */
export interface Conversation {
  id: string;
  title?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

/**
 * Shared chat state shape.
 *
 * This describes state only. It does not implement
 * any chat behavior.
 */
export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  conversationId?: string | null;
}
