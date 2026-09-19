import type { Metadata, Viewport } from "node_modules/next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "KING ZARRY AI",
    template: "%s | KING ZARRY AI",
  },
  description: "Your personal AI intelligence system.",
  keywords: [
    "AI",
    "Intelligence System",
    "Voice",
    "Vision",
    "Agents",
    "Markets",
    "Signals",
    "Command Centre",
  ],
  authors: [{ name: "King" }],
  creator: "King",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://kingzarry.ai",
    title: "KING ZARRY AI",
    description: "Your personal AI intelligence system.",
    siteName: "KING ZARRY AI",
  },
  twitter: {
    card: "summary_large_image",
    title: "KING ZARRY AI",
    description: "Your personal AI intelligence system.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1.0,
  maximumScale: 5.0,
  userScalable: true,
  themeColor: "#03060a",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="kz-bg-deepspace min-h-screen antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
        {/* Cinematic & Technical Atmospheric Global Layers */}
        <div className="kz-vignette" aria-hidden="true" />
        <div className="kz-scanline" aria-hidden="true" />
        <div className="fixed inset-0 kz-grid opacity-40 pointer-events-none z-0" aria-hidden="true" />

        {/* Global Application Environment Shell */}
        <div className="kz-app-shell relative z-10 flex flex-col min-h-screen w-full overflow-x-hidden">
          <main className="kz-app-content flex-1 flex flex-col w-full">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
