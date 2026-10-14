import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Start cTrader OAuth as a real browser redirect.
 *
 * The generic /api/* rewrite can proxy the provider's authorization page back
 * under the King Zarry origin on some runtimes. That breaks cTrader's login
 * session/CSRF flow and can end in "419 | PAGE EXPIRED". Fetch the Railway
 * endpoint without following redirects, then return its Location to the
 * browser as an actual 302 navigation.
 */
export async function GET(request: NextRequest) {
  const upstream = (
    process.env.API_UPSTREAM ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "https://fast-production-0eba.up.railway.app"
  ).trim().replace(/\/+$/, "");

  try {
    const response = await fetch(`${upstream}/api/ctrader/connect`, {
      method: "GET",
      headers: {
        cookie: request.headers.get("cookie") || "",
        accept: "text/html,application/json",
      },
      cache: "no-store",
      redirect: "manual",
    });

    const location = response.headers.get("location");
    if (response.status >= 300 && response.status < 400 && location) {
      const destination = new URL(location);
      if (destination.protocol !== "https:" || destination.hostname !== "id.ctrader.com") {
        return new NextResponse("Unexpected cTrader authorization redirect.", { status: 502 });
      }
      return NextResponse.redirect(destination, 302);
    }

    const detail = await response.text();
    return new NextResponse(
      response.ok ? "The cTrader authorization endpoint did not return a redirect. Please check Railway configuration." :
        `Could not start cTrader authorization (HTTP ${response.status}). ${detail.slice(0, 500)}`,
      { status: response.ok ? 502 : response.status, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  } catch {
    return new NextResponse("Could not reach the King Zarry AI cTrader service. Please try again shortly.", { status: 502 });
  }
}
