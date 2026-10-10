import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const API_UPSTREAM = (
  process.env.API_UPSTREAM ||
  process.env.BACKEND_URL ||
  "https://fast-production-0eba.up.railway.app"
).trim().replace(/\/+$/, "");

export async function GET(request: Request) {
  const incoming = new URL(request.url);
  const upstreamUrl = new URL(`/api/connectors/shopify/start${incoming.search}`, API_UPSTREAM);
  const headers = new Headers();
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("cookie", cookie);
  headers.set("accept", "application/json");
  headers.set("origin", incoming.origin);
  headers.set("referer", request.headers.get("referer") || `${incoming.origin}/dashboard`);

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      method: "GET",
      headers,
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Could not reach the King Zarry AI connector backend." },
      { status: 502, headers: { "Cache-Control": "no-store" } }
    );
  }

  const location = upstream.headers.get("location");
  if (upstream.status >= 300 && upstream.status < 400 && location) {
    return new Response(null, {
      status: upstream.status,
      headers: {
        Location: location,
        "Cache-Control": "no-store",
        "Referrer-Policy": "strict-origin-when-cross-origin",
      },
    });
  }

  const body = await upstream.arrayBuffer();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") || "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
