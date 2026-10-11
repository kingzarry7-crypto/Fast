import { after } from "next/server";
import { getToken } from "@vercel/connect";
import { createConnectWebhookVerifier } from "@vercel/connect/chat";

export const runtime = "nodejs";
export const maxDuration = 60;

const CONNECTOR = process.env.SLACK_CONNECTOR || "slack/cordovan-lamp";
const BACKEND_URL = (process.env.KING_ZARRY_BACKEND_URL || "https://fast-production-0eba.up.railway.app").replace(/\/$/, "");
const verifyConnectWebhook = createConnectWebhookVerifier();

type SlackEvent = {
  type?: string;
  user?: string;
  channel?: string;
  channel_type?: string;
  text?: string;
  ts?: string;
  thread_ts?: string;
  bot_id?: string;
  subtype?: string;
};

function cleanPrompt(text: string): string {
  return text
    .replace(/<@[A-Z0-9]+>/g, " ")
    .replace(/<#[A-Z0-9]+\|([^>]+)>/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

async function handleSlackEvent(event: SlackEvent): Promise<void> {
  if (!event.channel || !event.user || event.bot_id || event.subtype) return;
  const prompt = cleanPrompt(event.text || "");
  if (!prompt) return;

  const bridgeKey = process.env.KING_ZARRY_SLACK_BRIDGE_KEY;
  if (!bridgeKey) throw new Error("KING_ZARRY_SLACK_BRIDGE_KEY is not configured");

  const bridgeResponse = await fetch(`${BACKEND_URL}/api/slack/vercel`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-King-Zarry-Bridge-Key": bridgeKey,
    },
    body: JSON.stringify({ user_id: event.user, prompt }),
    signal: AbortSignal.timeout(50_000),
  });

  const bridgeData = await bridgeResponse.json().catch(() => ({})) as {
    ok?: boolean;
    response?: string;
    error?: string;
  };
  if (!bridgeResponse.ok || !bridgeData.ok || !bridgeData.response) {
    throw new Error(`King Zarry backend failed (${bridgeResponse.status}): ${bridgeData.error || "no_response"}`);
  }

  const token = await getToken(CONNECTOR, {
    subject: { type: "app" },
    scopes: ["chat:write"],
  });

  const threadTs = event.thread_ts || (event.channel_type === "im" ? undefined : event.ts);
  const slackResponse = await fetch("https://slack.com/api/chat.postMessage", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=utf-8",
    },
    body: JSON.stringify({
      channel: event.channel,
      text: bridgeData.response.slice(0, 39000),
      ...(threadTs ? { thread_ts: threadTs } : {}),
    }),
    signal: AbortSignal.timeout(15_000),
  });

  const slackData = await slackResponse.json().catch(() => ({})) as { ok?: boolean; error?: string };
  if (!slackResponse.ok || !slackData.ok) {
    throw new Error(`Slack reply failed: ${slackData.error || slackResponse.status}`);
  }
}

export async function POST(request: Request): Promise<Response> {
  const rawBody = await request.text();

  try {
    await verifyConnectWebhook(request, rawBody);
  } catch {
    return Response.json({ ok: false, error: "invalid_connect_signature" }, { status: 401 });
  }

  let payload: {
    type?: string;
    event_id?: string;
    challenge?: string;
    event?: SlackEvent;
  };
  try {
    payload = JSON.parse(rawBody);
  } catch {
    return Response.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  if (payload.type === "url_verification") {
    return Response.json({ challenge: payload.challenge || "" });
  }
  if (payload.type !== "event_callback") return Response.json({ ok: true });
  const event = payload.event || {};
  if (event.type !== "app_mention" && !(event.type === "message" && event.channel_type === "im")) {
    return Response.json({ ok: true, ignored: true });
  }
  if (event.bot_id || event.subtype || !event.user || !event.channel) {
    return Response.json({ ok: true, ignored: true });
  }

  after(async () => {
    try {
      await handleSlackEvent(event);
    } catch (error) {
      console.error("[King Zarry Slack bridge]", error);
    }
  });

  return Response.json({ ok: true, accepted: true, event_id: payload.event_id });
}
