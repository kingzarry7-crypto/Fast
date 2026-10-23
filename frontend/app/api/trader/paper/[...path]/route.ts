import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const allowedPaths = new Set(["status", "signals"]);

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (path.length !== 1 || !allowedPaths.has(path[0])) {
    return NextResponse.json({ detail: "Unknown Trader paper endpoint" }, { status: 404 });
  }
  const upstream = (
    process.env.API_UPSTREAM ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "https://fast-production-0eba.up.railway.app"
  ).trim().replace(/\\/+$/, "");
  const url = new URL("/multi-paper/" + path[0], upstream);
  request.nextUrl.searchParams.forEach((value, key) => url.searchParams.append(key, value));
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        cookie: request.headers.get("cookie") || "",
        accept: "application/json",
      },
      cache: "no-store",
      redirect: "manual",
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") || "application/json; charset=utf-8", "cache-control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "Could not reach the Railway paper-trading API" }, { status: 502 });
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}
