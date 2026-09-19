import type { Metadata } from "next";
import { ReactNode } from "react";
import "./globals.css";
export const metadata: Metadata = {
  title: {
    default: "KING ZARRY AI",
    template: "%s | KING ZARRY AI",
  },
  description:
    "KING ZARRY AI is an intelligent AI command centre for analysis, conversations, market intelligence, and AI-powered tools.",
  applicationName: "KING ZARRY AI",
  keywords: [
    "KING ZARRY AI",
    "AI assistant",
    "AI analysis",
    "market intelligence",
    "trading analysis",
  ],
  authors: [{ name: "KING ZARRY AI" }],
  creator: "KING ZARRY AI",
  publisher: "KING ZARRY AI",
  robots: {
    index: true,
    follow: true,
  },
  viewport: {
    width: "device-width",
    initialScale: 1,
  },
};
export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
