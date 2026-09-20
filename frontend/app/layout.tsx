import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: {
    default: "KING ZARRY AI",
    template: "%s | KING ZARRY AI",
  },
  description:
    "KING ZARRY AI — intelligent AI command centre for analysis, conversations, market intelligence, and AI-powered tools.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="kz-bg-grid" />
        <div className="kz-bg-radial" />
        <div className="relative z-10 flex min-h-screen">
          <Sidebar />
          <main className="flex-1 min-w-0">{children}</main>
        </div>
      </body>
    </html>
  );
}
