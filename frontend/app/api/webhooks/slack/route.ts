import { createHmac, timingSafeEqual } from "node:crypto";
import { after } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60;

const BACKEND_URL = (
  process.env.KING_ZARRY_BACKEND_URL ||
  "https://fast-production-0eba.up.railway.app"
).replace(/\/$/, "");

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

type SlackPayload = {
  type?: string;
  event_id?: string;
  challenge?: string;
  event?: SlackEvent;
};

function cleanPrompt(text: string): string {
  return text
    .replace(/<@[A-Z0-9]+>/g, " ")
    .replace(/<#[A-Z0-9]+\|([^>]+)>/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

function verifySlackRequest(request: Request, rawBody: string): boolean {
  const secret = process.env.SLACK_SIGNING_SECRET;
  const timestamp = request.headers.get("x-slack-request-timestamp");
  const signature = request.headers.get("x-slack-signature");
  if (!secret || !timestamp || !signature || !/^v0=[a-f0-9]{64}$/i.test(signature)) {
    return false;
  }

  const timestampSeconds = Number(timestamp);
  if (!Number.isSafeInteger(timestampSeconds) ||
      Math.abs(Date.now() / 1000 - timestampSeconds) > 60 * 5) {
    return false;
  }

  const baseString = `v0:${timestamp}:${rawBody}`;
  const expected = `v0=${createHmac("sha256", secret).update(baseString).digest("hex")}`;
  const expectedBuffer = Buffer.from(expected, "utf8");
  const suppliedBuffer = Buffer.from(signature, "utf8");
  return expectedBuffer.length === suppliedBuffer.length &&
    timingSafeEqual(expectedBuffer, suppliedBuffer);
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

  const botToken = process.env.SLACK_BOT_TOKEN;
  if (!botToken) throw new Error("SLACK_BOT_TOKEN is not configured");

  const threadTs = event.thread_ts || (event.channel_type === "im" ? undefined : event.ts);
  const slackResponse = await fetch("https://slack.com/api/chat.postMessage", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${botToken}`,
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
  if (!verifySlackRequest(request, rawBody)) {
    return Response.json({ ok: false, error: "invalid_slack_signature" }, { status: 401 });
  }

  let payload: SlackPayload;
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
