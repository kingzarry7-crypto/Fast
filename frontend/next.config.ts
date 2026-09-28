import type { NextConfig } from "next";

const apiProxyTarget = process.env.API_PROXY_TARGET;

const nextConfig: NextConfig = {
  // Base44 preview: allow the public preview origin to load dev assets/HMR
  ...(process.env.BASE44_PUBLIC_HOST_SUFFIX
    ? { allowedDevOrigins: [`3000-${process.env.BASE44_PUBLIC_HOST_SUFFIX}`] }
    : {}),
  // Optional same-origin proxy to the API (used by the Base44 dev compose)
  ...(apiProxyTarget
    ? {
        experimental: { proxyTimeout: 180_000 },
        async rewrites() {
          return [
            { source: "/api/:path*", destination: `${apiProxyTarget}/api/:path*` },
            { source: "/health", destination: `${apiProxyTarget}/health` },
          ];
        },
      }
    : {}),
  // Allow cross-origin requests to the Railway backend
  async headers() {
    return [
      {
        source: "/api/:path*",
        headers: [
          { key: "Access-Control-Allow-Credentials", value: "true" },
          { key: "Access-Control-Allow-Origin", value: process.env.NEXT_PUBLIC_API_BASE_URL || "*" },
        ],
      },
    ];
  },
};

export default nextConfig;
