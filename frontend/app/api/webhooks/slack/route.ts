/**
 * Cloudflare-friendly Slack Events proxy.
 *
 * Slack signs the exact raw request body. Forward it unchanged, together with
 * the original signature headers, so Railway's /api/slack/events endpoint can
 * perform the authoritative signature check and event deduplication.
 */
export const runtime = "nodejs";
export const maxDuration = 15;

const BACKEND_URL = (
  process.env.KING_ZARRY_BACKEND_URL ||
  "https://fast-production-0eba.up.railway.app"
).trim().replace(/\/+$/, "");

export async function POST(request: Request): Promise<Response> {
  const rawBody = await request.text();
  const timestamp = request.headers.get("x-slack-request-timestamp");
  const signature = request.headers.get("x-slack-signature");

  if (!timestamp || !signature) {
    return Response.json({ ok: false, error: "missing_slack_signature" }, { status: 401 });
  }

  try {
    const upstream = await fetch(`${BACKEND_URL}/api/slack/events`, {
      method: "POST",
      headers: {
        "Content-Type": request.headers.get("content-type") || "application/json",
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
      },
      body: rawBody,
      signal: AbortSignal.timeout(10_000),
      cache: "no-store",
    });

    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json({ ok: false, error: "slack_backend_unavailable" }, { status: 502 });
  }
}
