"use client";

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import Link from "next/link";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatResponse {
  reply?: string;
  response?: string;
  message?: string;
  detail?: string;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://fast-production-0eba.up.railway.app";

export default function LiveChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Scanning neural pathways… Ready for your query.",
    },
  ]);

  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState(false);

  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  }, [messages, loading]);

  async function handleSubmit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();

    const trimmed = input.trim();

    if (!trimmed || loading) {
      return;
    }

    setInput("");
    setAuthError(false);

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: trimmed,
      },
    ]);

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: trimmed,
        }),
      });

      let data: ChatResponse = {};

      try {
        data = await response.json();
      } catch {
        data = {};
      }

      if (response.status === 401) {
        setAuthError(true);

        setMessages((previous) => [
          ...previous,
          {
            role: "assistant",
            content:
              "LOGIN REQUIRED: Sign in to continue your conversation with KING ZARRY AI.",
          },
        ]);

        return;
      }

      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.reply ||
            data.response ||
            "KING ZARRY AI is temporarily unavailable."
        );
      }

      const reply =
        data.reply ||
        data.response ||
        data.message ||
        "KING ZARRY AI returned an empty response.";

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: reply,
        },
      ]);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Unable to connect to KING ZARRY AI.";

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: errorMessage,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      if (!loading && input.trim()) {
        event.currentTarget.form?.requestSubmit();
      }
    }
  }

  return (
    <div
      className="kz-console"
      style={{
        width: "100%",
        maxWidth: "900px",
        margin: "0 auto",
      }}
    >
      {/* CHANNEL HEADER */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          marginBottom: "18px",
          paddingBottom: "12px",
          borderBottom: "1px solid rgba(79,216,255,.14)",
        }}
      >
        <div className="kz-hud-label">
          SECURE CHANNEL
        </div>

        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "7px",
            color: "#67f5b4",
            fontSize: "0.65rem",
            fontWeight: 700,
            letterSpacing: "0.14em",
          }}
        >
          <span
            aria-hidden="true"
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              background: "#67f5b4",
              boxShadow: "0 0 12px rgba(103,245,180,.8)",
            }}
          />

          LIVE SESSION
        </span>
      </div>

      {/* MESSAGES */}
      <div
        className="kz-chat-messages"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "20px",
          marginBottom: "20px",
          maxHeight: "400px",
          overflowY: "auto",
          paddingRight: "4px",
        }}
      >
        {messages.map((message, index) => {
          if (message.role === "user") {
            return (
              <div
                className="kz-msg-user"
                key={`${index}-user`}
              >
                <span className="kz-who">USER</span>

                <p>{message.content}</p>
              </div>
            );
          }

          const isLastMessage =
            index === messages.length - 1;

          return (
            <div
              className="kz-msg-ai"
              key={`${index}-assistant`}
            >
              <div
                className="kz-ai-orb"
                aria-hidden="true"
              >
                <span />
              </div>

              <div className="kz-ai-body">
                <span className="kz-who">
                  KZ AI
                </span>

                <p className="kz-line">
                  {message.content}
                </p>

                {authError && isLastMessage && (
                  <div style={{ marginTop: "12px" }}>
                    <Link
                      href="/login"
                      className="kz-btn kz-btn-primary"
                      style={{
                        padding: "8px 16px",
                        minHeight: "36px",
                        fontSize: "0.66rem",
                      }}
                    >
                      <span>
                        SIGN IN TO SYSTEM
                      </span>
                    </Link>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* THINKING STATE */}
        {loading && (
          <div className="kz-msg-ai">
            <div
              className="kz-ai-orb"
              aria-hidden="true"
            >
              <span />
            </div>

            <div className="kz-ai-body">
              <span className="kz-who">
                KZ AI
              </span>

              <p className="kz-line">
                THINKING...
                <span
                  className="kz-caret"
                  aria-hidden="true"
                />
              </p>
            </div>
          </div>
        )}

        <div ref={scrollRef} />
      </div>

      {/* INPUT */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          gap: "10px",
          marginTop: "16px",
          borderTop:
            "1px solid rgba(79,216,255,.14)",
          paddingTop: "16px",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(event) =>
            setInput(event.target.value)
          }
          onKeyDown={handleKeyDown}
          disabled={loading}
          autoComplete="off"
          placeholder="Ask your intelligence..."
          aria-label="Ask KING ZARRY AI"
          style={{
            flex: 1,
            minWidth: 0,
            background:
              "rgba(255,255,255,.04)",
            border:
              "1px solid rgba(79,216,255,.28)",
            borderRadius: "2px",
            padding: "12px 16px",
            color: "#eaf6fb",
            fontFamily: "inherit",
            fontSize: "0.9rem",
            outline: "none",
          }}
        />

        <button
          type="submit"
          disabled={
            loading || !input.trim()
          }
          className="kz-btn kz-btn-primary"
          style={{
            padding: "12px 20px",
            minHeight: "auto",
            opacity:
              loading || !input.trim()
                ? 0.6
                : 1,
            cursor:
              loading || !input.trim()
                ? "not-allowed"
                : "pointer",
          }}
        >
          <span>
            {loading ? "THINKING..." : "SEND"}
          </span>
        </button>
      </form>
    </div>
  );
}
