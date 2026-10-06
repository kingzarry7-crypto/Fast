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
  // Safe production fallback so Connected Accounts does not break when the
  // Vercel environment variable is missing. Override with API_UPSTREAM when
  // deploying a different backend.
  "https://fast-production-0eba.up.railway.app"
)
  .trim()
  .replace(/\/+$/, "");

const nextConfig: NextConfig = {
  // Additive security headers. No CSP is forced here because the app uses
  // several runtime integrations and we do not want to break existing UI.
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(self), microphone=(self), geolocation=()" },
      ],
    }];
  },
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
