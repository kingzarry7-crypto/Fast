import type { NextConfig } from "next";

/**
 * Mobile Safari/Chrome block cross-site cookies (Vercel → Railway).
 * Rewrite /api/* to the Railway backend so the browser talks to the SAME
 * origin (vercel.app) and session cookies stick.
 *
 * Vercel env (Production):
 *   API_UPSTREAM=https://YOUR-service.up.railway.app
 *   NEXT_PUBLIC_API_BASE_URL=   (leave EMPTY)
 *   NEXT_PUBLIC_API_SAME_ORIGIN=true
 */
const API_UPSTREAM = (
  process.env.API_UPSTREAM ||
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  ""
)
  .trim()
  .replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    if (!API_UPSTREAM) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${API_UPSTREAM}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${API_UPSTREAM}/health`,
      },
    ];
  },
};

export default nextConfig;
